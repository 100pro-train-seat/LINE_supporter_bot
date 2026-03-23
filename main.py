import logging
import os
import threading
import time

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from api_client import (
    find_most_supporter_car,
    get_internal_messages,
    get_match_list,
    register_supporter_seat,
    send_seat_request,
)
from messages import (
    VALID_SEAT_COLUMNS,
    ask_carriage,
    ask_confirm,
    ask_request_carriage,
    ask_seat_column,
    ask_seat_row,
    ask_taker_train_id,
    ask_train_id,
    push_give,
    push_thanks,
    reply_cancelled,
    reply_default,
    reply_error,
    reply_match_accepted,
    reply_match_empty,
    reply_match_list,
    reply_request_failed,
    reply_request_sent,
    reply_success,
    reply_taker_not_found,
    reply_taker_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s – %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

sessions: dict = {}

PUSH_HANDLERS = {
    "give":   push_give,
    "thanks": push_thanks,
}

POLLING_INTERVAL = 5  # 秒


def _poll_internal_messages():
    """バックグラウンドで定期的に内部メッセージを確認し、LINE にプッシュ通知する。"""
    while True:
        try:
            for msg in get_internal_messages():
                uid      = msg.get("line_user_id")
                msg_type = msg.get("type")
                handler_fn = PUSH_HANDLERS.get(msg_type)
                if uid and handler_fn:
                    line_bot_api.push_message(uid, handler_fn())
                    logger.info("Pushed %s to %s", msg_type, uid)
                else:
                    logger.warning("Unknown message type: %s", msg_type)
        except Exception as exc:
            logger.error("Polling error: %s", exc)
        time.sleep(POLLING_INTERVAL)


# バックグラウンドでポーリングを開始（関数定義の後に記述）
threading.Thread(target=_poll_internal_messages, daemon=True).start()

SUPPORTER_KEYWORDS  = {"乗車情報登録", "登録", "register", "start"}
CANDIDATE_KEYWORDS  = {"号車を探す", "席を探す", "テイカー", "find", "search"}
REQUEST_KEYWORDS    = {"座席リクエスト", "リクエスト"}
CHECK_KEYWORDS      = {"依頼確認"}
RANK_KEYWORDS       = {"ランクを確認する"}
CANCEL_KEYWORDS     = {"キャンセル", "cancel", "中断", "やめる"}


def reply(token, message):
    line_bot_api.reply_message(token, message)


@app.get("/health")
def health():
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

    # サポーター：ランク確認（準備中）
    if text in RANK_KEYWORDS:
        from linebot.models import TextSendMessage as TSM
        reply(token, TSM(text="🏅 ランク確認機能は準備中です。\nしばらくお待ちください。"))
        return

    # サポーター：依頼確認（一発取得）
    if text in CHECK_KEYWORDS:
        asking = get_match_list(line_user_id=user_id)
        if asking is None:
            reply(token, reply_error())
        elif len(asking) == 0:
            reply(token, reply_match_empty())
        else:
            reply(token, reply_match_list(asking))
        return

    # サポーター：依頼を受理する（「受理する {ID}」形式）
    if text.startswith("受理する "):
        asking_id = text.split(" ", 1)[1]
        # TODO: バックエンドの受理エンドポイントが提供され次第、ここに実装する
        # 例: accept_match(line_user_id=user_id, asking_id=asking_id)
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
        train_id = text
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
            reply(token, reply_request_sent() if success else reply_request_failed())
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
            session["step"]       = "seat_column"
            reply(token, ask_seat_column())
        else:
            reply(token, ask_carriage())

    elif step == "seat_column":
        col = text.upper()
        if col in VALID_SEAT_COLUMNS:
            session["seat_col"] = col
            session["step"]     = "seat_row"
            reply(token, ask_seat_row())
        else:
            reply(token, ask_seat_column())

    elif step == "seat_row":
        if text.isdigit() and 1 <= int(text) <= 99:
            session["seat_number"] = f"{session['seat_col']}{text}"
            session["step"]        = "confirm"
            reply(token, ask_confirm(session))
        else:
            reply(token, TextSendMessage(text="番号を数字で入力してください（例：12）"))

    elif step == "confirm":
        if text == "✅ 登録する":
            success = register_supporter_seat(
                line_user_id=user_id,
                train_id=session["train_id"],
                car_number=session["car_number"],
                seat_number=session["seat_number"],
            )
            sessions.pop(user_id, None)
            reply(token, reply_success(session) if success else reply_error())

        elif text == "🔄 やり直す":
            sessions[user_id] = {"step": "train_id"}
            reply(token, ask_train_id())

        else:
            reply(token, TextSendMessage(text='「✅ 登録する」または「🔄 やり直す」を選んでください。'))
