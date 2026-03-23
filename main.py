"""FastAPI application – LINE Webhook handler for supporter seat registration."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()  # api_client インポート前に環境変数を読み込む

from fastapi import FastAPI, HTTPException, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from api_client import register_supporter_seat
from messages import (
    VALID_SEAT_COLUMNS,
    ask_carriage,
    ask_confirm,
    ask_seat_column,
    ask_seat_row,
    ask_train_id,
    reply_cancelled,
    reply_default,
    reply_error,
    reply_success,
)
from session import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ITO Train – Supporter Bot")

line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler      = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
sessions     = SessionManager()

TRIGGER_KEYWORDS = {"乗車情報登録", "登録", "register", "start"}
CANCEL_KEYWORDS  = {"キャンセル", "cancel", "中断", "やめる"}


# ─────────────────────────────────────────────────────────────────
def _start_registration(reply_token: str, user_id: str) -> None:
    sessions.set(user_id, {"step": "train_id"})
    line_bot_api.reply_message(reply_token, ask_train_id())


# ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request) -> str:
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"


# ─────────────────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent) -> None:
    user_id     = event.source.user_id
    text        = event.message.text.strip()
    reply_token = event.reply_token
    session     = sessions.get(user_id)

    # ── キャンセル ────────────────────────────────────────────────
    if text in CANCEL_KEYWORDS:
        sessions.delete(user_id)
        line_bot_api.reply_message(reply_token, reply_cancelled())
        return

    # ── 登録フロー開始 ────────────────────────────────────────────
    if text in TRIGGER_KEYWORDS:
        _start_registration(reply_token, user_id)
        return

    # ── セッションなし ────────────────────────────────────────────
    if session is None:
        line_bot_api.reply_message(reply_token, reply_default())
        return

    step = session.get("step")

    # ── Step 1: 列車ID ────────────────────────────────────────────
    if step == "train_id":
        session["train_id"] = text
        session["step"]     = "carriage"
        sessions.set(user_id, session)
        line_bot_api.reply_message(reply_token, ask_carriage())

    # ── Step 2: 号車 ──────────────────────────────────────────────
    elif step == "carriage":
        if text.isdigit() and 1 <= int(text) <= 6:
            session["car_number"] = text   # 数字のみ（例: "3"）
            session["step"]       = "seat_column"
            sessions.set(user_id, session)
            line_bot_api.reply_message(reply_token, ask_seat_column())
        else:
            line_bot_api.reply_message(reply_token, ask_carriage())

    # ── Step 3: 座席列（A〜E）────────────────────────────────────
    elif step == "seat_column":
        col = text.upper()
        if col in VALID_SEAT_COLUMNS:
            session["seat_col"] = col
            session["step"]     = "seat_row"
            sessions.set(user_id, session)
            line_bot_api.reply_message(reply_token, ask_seat_row())
        else:
            line_bot_api.reply_message(reply_token, ask_seat_column())

    # ── Step 4: 座席番号（行）────────────────────────────────────
    elif step == "seat_row":
        if text.isdigit() and 1 <= int(text) <= 99:
            # "A" + "12" → "A12"
            session["seat_number"] = f"{session['seat_col']}{text}"
            session["step"]        = "confirm"
            sessions.set(user_id, session)
            line_bot_api.reply_message(reply_token, ask_confirm(session))
        else:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="番号を数字で入力してください（例：12）"),
            )

    # ── Step 5: 確認・登録 ────────────────────────────────────────
    elif step == "confirm":
        if text == "✅ 登録する":
            success = register_supporter_seat(
                line_user_id=user_id,
                train_id=session["train_id"],
                car_number=session["car_number"],
                seat_number=session["seat_number"],
            )
            sessions.delete(user_id)
            line_bot_api.reply_message(
                reply_token,
                reply_success(session) if success else reply_error(),
            )

        elif text == "🔄 やり直す":
            sessions.delete(user_id)
            _start_registration(reply_token, user_id)

        else:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text='「✅ 登録する」または「🔄 やり直す」を選んでください。'),
            )
