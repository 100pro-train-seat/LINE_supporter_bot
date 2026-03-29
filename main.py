import logging
import os
import threading
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from api_client import (
    accept_match,
    cancel_match_request,
    complete_match,
    delete_supporter_seat,
    find_most_supporter_car,
    get_internal_messages,
    get_last_error,
    get_match_list,
    get_matched,
    get_trains,
    get_user_profile,
    register_supporter_seat,
    search_stations,
    send_seat_request,
)
from messages import (
    VALID_SEAT_POSITIONS,
    ask_carriage,
    ask_confirm,
    ask_request_carriage,
    ask_seat_position,
    ask_station_keyword,
    ask_station_select,
    ask_train_select,
    push_canceled,
    push_match,
    push_thanks,
    reply_candidate_success,
    reply_cancelled,
    reply_default,
    reply_match_empty,
    reply_match_list,
    reply_rank,
    reply_request_sent,
    reply_station_not_found,
    reply_success,
    reply_taker_not_found,
    reply_taker_result,
    reply_train_not_found,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s – %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # 秒

PUSH_HANDLERS = {
    "canceled": push_canceled,
}


def poll_internal_messages():
    """/internal/messages を定期的にポーリングしてLINEプッシュ通知を送る。"""
    print("POLLING THREAD STARTED", flush=True)
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            logger.info("Polling /internal/messages...")
            messages = get_internal_messages()
            for msg in messages:
                uid      = msg.get("line_user_id")
                msg_type = msg.get("type")
                if not uid or not msg_type:
                    continue
                if msg_type == "give":
                    asking = get_match_list(line_user_id=uid)
                    if asking:
                        line_bot_api.push_message(uid, reply_match_list(asking))
                        logger.info("Pushed give(match list) to %s", uid)
                elif msg_type == "match":
                    result = get_matched(line_user_id=uid)
                    if result:
                        line_bot_api.push_message(uid, push_match(
                            car_number=result.get("car_number", ""),
                            seat_number=result.get("seat_number", ""),
                        ))
                        logger.info("Pushed match to %s", uid)
                elif msg_type == "thanks":
                    profile = get_user_profile(line_user_id=uid)
                    matched_count = profile.get("matched_count", 0) if profile else 0
                    point = profile.get("point", 0) if profile else 0
                    line_bot_api.push_message(uid, push_thanks(matched_count=matched_count, point=point))
                    logger.info("Pushed thanks to %s", uid)
                else:
                    handler_fn = PUSH_HANDLERS.get(msg_type)
                    if handler_fn:
                        line_bot_api.push_message(uid, handler_fn())
                        logger.info("Pushed %s to %s", msg_type, uid)
        except Exception as exc:
            logger.error("Polling error: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    t = threading.Thread(target=poll_internal_messages, daemon=True)
    t.start()
    print("POLLING THREAD LAUNCHED", flush=True)
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

sessions: dict = {}

SUPPORTER_KEYWORDS = {"乗車情報登録", "登録", "supporter", "start","regist"}
CANDIDATE_KEYWORDS = {"問い合わせ", "探す", "席を探す", "taker", "find", "search"}
REQUEST_KEYWORDS   = {"座席リクエスト", "リクエスト"}
CHECK_KEYWORDS     = {"リクエスト確認","依頼確認"}
RANK_KEYWORDS      = {"ランクを確認", "ランクを確認する", "ランク確認", "rank"}
CANCEL_KEYWORDS         = {"キャンセル", "cancel", "中断", "やめる","終わる"}
MATCH_CANCEL_KEYWORDS   = {"リクエストキャンセル"}
SEAT_DELETE_KEYWORDS    = {"登録削除"}


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

    # 依頼者：リクエストキャンセル
    if text in MATCH_CANCEL_KEYWORDS:
        success = cancel_match_request(line_user_id=user_id)
        reply(token, TextSendMessage(text="✅ リクエストをキャンセルしました。") if success else TextSendMessage(text=f"❌ {get_last_error()}"))
        return

    # サポーター：座席登録削除
    if text in SEAT_DELETE_KEYWORDS:
        success = delete_supporter_seat(line_user_id=user_id)
        reply(token, TextSendMessage(text="✅ 座席登録を削除しました。") if success else TextSendMessage(text=f"❌ {get_last_error()}"))
        return

    # サポーター：乗車情報登録フロー開始
    if text in SUPPORTER_KEYWORDS:
        sessions[user_id] = {"step": "station_keyword", "flow": "supporter"}
        reply(token, ask_station_keyword())
        return

    # 依頼者：候補問い合わせフロー開始
    if text in CANDIDATE_KEYWORDS:
        sessions[user_id] = {"step": "station_keyword", "flow": "taker"}
        reply(token, ask_station_keyword())
        return

    # 依頼者：座席リクエストフロー開始
    if text in REQUEST_KEYWORDS:
        sessions[user_id] = {"step": "station_keyword", "flow": "request"}
        reply(token, ask_station_keyword())
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

    # サポーター：依頼に立候補（「受理する {ID}」形式）
    if text.startswith("受理する "):
        match_id = text.split(" ", 1)[1]
        success = accept_match(line_user_id=user_id, match_id=match_id)
        reply(token, reply_candidate_success() if success else TextSendMessage(text=f"❌ {get_last_error()}"))
        return

    # テイカー：リクエスト完了
    if text == "✅ リクエスト完了":
        success = complete_match(line_user_id=user_id)
        reply(token, TextSendMessage(text="🙏 リクエストが完了しました！\nサポーターにお礼が届きます。") if success else TextSendMessage(text=f"❌ {get_last_error()}"))
        return

    # セッションなし
    if session is None:
        reply(token, reply_default())
        return

    step = session["step"]
    flow = session.get("flow")

    # ── 駅名検索（共通） ──────────────────────────────────────────
    if step == "station_keyword":
        stations = search_stations(line_user_id=user_id, keyword=text)
        if stations is None:
            reply_error(token)
        elif len(stations) == 0:
            reply(token, reply_station_not_found())
        else:
            session["stations"] = stations[:5]
            session["step"]     = "station_select"
            reply(token, ask_station_select(session["stations"]))

    # ── 駅選択（共通） ────────────────────────────────────────────
    elif step == "station_select":
        stations = session.get("stations", [])
        if text.isdigit() and 1 <= int(text) <= len(stations):
            station = stations[int(text) - 1]
            trains = get_trains(line_user_id=user_id, station_id=station["id"])
            if trains is None:
                reply_error(token)
            elif len(trains) == 0:
                reply(token, reply_train_not_found())
            else:
                session["trains"] = trains
                session["step"]   = "train_select"
                reply(token, ask_train_select(trains))
        else:
            reply(token, ask_station_select(stations))

    # ── 列車選択（共通） ──────────────────────────────────────────
    elif step == "train_select":
        trains = session.get("trains", [])
        if text.isdigit() and 1 <= int(text) <= len(trains):
            train = trains[int(text) - 1]
            session["train_id"]      = train["train_id"]
            session["train_display"] = f"{train['time'][:5]} → {train['destination']}"
            if flow == "supporter":
                session["step"] = "carriage"
                reply(token, ask_carriage())
            elif flow == "taker":
                train_id = train["train_id"]
                display  = session["train_display"]
                sessions.pop(user_id, None)
                car_number = find_most_supporter_car(line_user_id=user_id, train_id=train_id)
                if car_number is not None:
                    reply(token, reply_taker_result(display, car_number))
                else:
                    reply(token, reply_taker_not_found(display))
            elif flow == "request":
                session["step"] = "request_carriage"
                reply(token, ask_request_carriage())
        else:
            reply(token, ask_train_select(trains))

    # ── 座席リクエストフロー ──────────────────────────────────────
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
            sessions[user_id] = {"step": "station_keyword", "flow": "supporter"}
            reply(token, ask_station_keyword())

        else:
            reply(token, TextSendMessage(text='「✅ 登録する」または「🔄 やり直す」を選んでください。'))
