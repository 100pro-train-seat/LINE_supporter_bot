import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from api_client import find_most_supporter_car, register_supporter_seat
from messages import (
    VALID_SEAT_COLUMNS,
    ask_carriage,
    ask_confirm,
    ask_seat_column,
    ask_seat_row,
    ask_taker_train_id,
    ask_train_id,
    reply_cancelled,
    reply_default,
    reply_error,
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

SUPPORTER_KEYWORDS = {"乗車情報登録", "登録", "register", "start"}
TAKER_KEYWORDS     = {"席を探す", "テイカー", "find", "search"}
CANCEL_KEYWORDS    = {"キャンセル", "cancel", "中断", "やめる"}


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

    # サポーター登録フロー開始
    if text in SUPPORTER_KEYWORDS:
        sessions[user_id] = {"step": "train_id"}
        reply(token, ask_train_id())
        return

    # テイカーフロー開始
    if text in TAKER_KEYWORDS:
        sessions[user_id] = {"step": "taker_train_id"}
        reply(token, ask_taker_train_id())
        return

    # セッションなし
    if session is None:
        reply(token, reply_default())
        return

    step = session["step"]

    # ── テイカーフロー ────────────────────────────────────────────
    if step == "taker_train_id":
        train_id = text
        sessions.pop(user_id, None)
        car_number = find_most_supporter_car(line_user_id=user_id, train_id=train_id)
        if car_number is not None:
            reply(token, reply_taker_result(train_id, car_number))
        else:
            reply(token, reply_taker_not_found(train_id))

    # ── サポーターフロー ──────────────────────────────────────────
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
