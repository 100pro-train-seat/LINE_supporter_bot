import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from api_client import (
    find_most_supporter_car,
    get_last_error,
    get_match_list,
    get_user_profile,
    register_supporter_seat,
    send_seat_request,
)
from messages import (
    VALID_SEAT_POSITIONS,
    ask_carriage,
    ask_confirm,
    ask_request_carriage,
    ask_seat_position,
    ask_taker_train_id,
    ask_train_id,
    push_give,
    push_thanks,
    reply_cancelled,
    reply_default,
    reply_match_accepted,
    reply_match_empty,
    reply_match_list,
    reply_rank,
    reply_request_sent,
    reply_success,
    reply_taker_not_found,
    reply_taker_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s – %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

sessions: dict = {}

PUSH_HANDLERS = {
    "give":   push_give,
    "thanks": push_thanks,
}

SUPPORTER_KEYWORDS = {"乗車情報登録", "登録", "supporter", "start","regist"}
CANDIDATE_KEYWORDS = {"問い合わせ", "探す", "席を探す", "taker", "find", "search"}
REQUEST_KEYWORDS   = {"座席リクエスト", "リクエスト"}
CHECK_KEYWORDS     = {"リクエスト確認","依頼確認"}
RANK_KEYWORDS      = {"ランクを確認"}
CANCEL_KEYWORDS    = {"キャンセル", "cancel", "中断", "やめる","終わる"}


def reply(token, message):
    line_bot_api.reply_message(token, message)


def reply_error(token):
    reply(token, TextSendMessage(text=f"❌ {get_last_error()}"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/notify")
async def notify(request: Request):
    body = await request.json()
    uid        = body.get("line_user_id")
    handler_fn = PUSH_HANDLERS.get(body.get("type"))
    if not uid or not handler_fn:
        raise HTTPException(status_code=400, detail="Invalid payload")
    line_bot_api.push_message(uid, handler_fn())
    logger.info("Notified %s to %s", body.get("type"), uid)
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    user_id = event.source.user_id
    text    = event.message.text.strip()
    token   = event.reply_token
    session = sessions.get(user_id)

    # キャンセル
    if text in CANCEL_KEYWORDS:
        sessions.pop(user_id, None)
        reply(token, reply_cancelled())
        return

    # サポーター：乗車情報登録フロー開始
    if text in SUPPORTER_KEYWORDS:
        sessions[user_id] = {"step": "train_id"}
        reply(token, ask_train_id())
        return

    # テイカー：候補問い合わせフロー開始
    if text in CANDIDATE_KEYWORDS:
        sessions[user_id] = {"step": "taker_train_id"}
        reply(token, ask_taker_train_id())
        return

    # テイカー：座席リクエストフロー開始
    if text in REQUEST_KEYWORDS:
        sessions[user_id] = {"step": "request_train_id"}
        reply(token, ask_train_id())
        return

    # サポーター：ランク確認
    if text in RANK_KEYWORDS:
        profile = get_user_profile(line_user_id=user_id)
        if profile is None:
            reply_error(token)
        else:
            reply(token, reply_rank(
                matched_count=profile.get("matched_count", 0),
                point=profile.get("point", 0),
            ))
        return

    # サポーター：依頼確認
    if text in CHECK_KEYWORDS:
        asking = get_match_list(line_user_id=user_id)
        if asking is None:
            reply_error(token)
        elif len(asking) == 0:
            reply(token, reply_match_empty())
        else:
            reply(token, reply_match_list(asking))
        return

    # サポーター：依頼を受理する（「受理する {ID}」形式）
    if text.startswith("受理する "):
        asking_id = text.split(" ", 1)[1]
        # TODO: バックエンドの受理エンドポイントが提供され次第、ここに実装する
        logger.info("Accept request – user=%s asking_id=%s", user_id, asking_id)
        reply(token, reply_match_accepted())
        return

    # セッションなし
    if session is None:
        reply(token, reply_default())
        return

    step = session["step"]

    # ── 候補問い合わせフロー ──────────────────────────────────────
    if step == "taker_train_id":
        train_id   = text
        sessions.pop(user_id, None)
        car_number = find_most_supporter_car(line_user_id=user_id, train_id=train_id)
        if car_number is not None:
            reply(token, reply_taker_result(train_id, car_number))
        else:
            reply(token, reply_taker_not_found(train_id))

    # ── 座席リクエストフロー ──────────────────────────────────────
    elif step == "request_train_id":
        session["train_id"] = text
        session["step"]     = "request_carriage"
        reply(token, ask_request_carriage())

    elif step == "request_carriage":
        if text.isdigit() and 1 <= int(text) <= 6:
            success = send_seat_request(
                line_user_id=user_id,
                train_id=session["train_id"],
                car_number=text,
            )
            sessions.pop(user_id, None)
            reply(token, reply_request_sent() if success else TextSendMessage(text=f"❌ {get_last_error()}"))
        else:
            reply(token, ask_request_carriage())

    # ── サポーター登録フロー ──────────────────────────────────────
    elif step == "train_id":
        session["train_id"] = text
        session["step"]     = "carriage"
        reply(token, ask_carriage())

    elif step == "carriage":
        if text.isdigit() and 1 <= int(text) <= 6:
            session["car_number"] = text
            session["step"]       = "seat_position"
            reply(token, ask_seat_position())
        else:
            reply(token, ask_carriage())

    elif step == "seat_position":
        pos = text.upper()
        if pos in VALID_SEAT_POSITIONS:
            session["seat_number"] = pos
            session["step"]        = "confirm"
            reply(token, ask_confirm(session))
        else:
            reply(token, ask_seat_position())

    elif step == "confirm":
        if text == "✅ 登録する":
            success = register_supporter_seat(
                line_user_id=user_id,
                train_id=session["train_id"],
                car_number=session["car_number"],
                seat_number=session["seat_number"],
            )
            sessions.pop(user_id, None)
            reply(token, reply_success(session) if success else TextSendMessage(text=f"❌ {get_last_error()}"))

        elif text == "🔄 やり直す":
            sessions[user_id] = {"step": "train_id"}
            reply(token, ask_train_id())

        else:
            reply(token, TextSendMessage(text='「✅ 登録する」または「🔄 やり直す」を選んでください。'))
