"""LINE message builders with Quick Reply support."""
from typing import Any, Dict

from linebot.models import (
    MessageAction,
    PostbackAction,
    QuickReply,
    QuickReplyButton,
    TextSendMessage,
)

# 座席列（横浜市営地下鉄）
SEAT_COLUMNS = ["A", "B", "C", "D", "E"]

VALID_SEAT_COLUMNS = set(SEAT_COLUMNS)


def _qr_button(label: str, text: str) -> QuickReplyButton:
    return QuickReplyButton(action=MessageAction(label=label, text=text))


def _qr_postback(label: str, data: str) -> QuickReplyButton:
    return QuickReplyButton(action=PostbackAction(label=label, data=data))


# ── Step 1: 列車ID入力 ────────────────────────────────────────────
def ask_train_id() -> TextSendMessage:
    return TextSendMessage(
        text="🚇 乗車する列車IDを入力してください\n（例：A0002）"
    )


# ── Step 2: 号車（横浜市営地下鉄: 全6両編成）────────────────────
def ask_carriage(page: int = 1) -> TextSendMessage:
    items = [_qr_button(f"{i}号車", str(i)) for i in range(1, 7)]
    return TextSendMessage(
        text="🚃 何号車ですか？",
        quick_reply=QuickReply(items=items),
    )


# ── Step 3: 座席列（A〜E）────────────────────────────────────────
def ask_seat_column() -> TextSendMessage:
    items = [_qr_button(col, col) for col in SEAT_COLUMNS]
    return TextSendMessage(
        text="💺 座席の列を選んでください\n（A〜E）",
        quick_reply=QuickReply(items=items),
    )


# ── Step 4: 座席番号（行）────────────────────────────────────────
def ask_seat_row() -> TextSendMessage:
    return TextSendMessage(
        text="🔢 座席の番号を入力してください\n（例：12）"
    )


# ── Step 5: 確認 ─────────────────────────────────────────────────
def ask_confirm(session: Dict[str, Any]) -> TextSendMessage:
    train_id    = session.get("train_id", "")
    car_number  = session.get("car_number", "")
    seat_number = session.get("seat_number", "")

    body = (
        f"📋 以下の内容で登録しますか？\n\n"
        f"🚇 列車ID：{train_id}\n"
        f"🚃 号車：{car_number}号車\n"
        f"💺 座席：{seat_number}"
    )
    items = [
        _qr_button("✅ 登録する", "✅ 登録する"),
        _qr_button("🔄 やり直す", "🔄 やり直す"),
    ]
    return TextSendMessage(text=body, quick_reply=QuickReply(items=items))


# ── 結果 ─────────────────────────────────────────────────────────
def reply_success(session: Dict[str, Any]) -> TextSendMessage:
    train_id    = session.get("train_id", "")
    car_number  = session.get("car_number", "")
    seat_number = session.get("seat_number", "")
    return TextSendMessage(
        text=(
            f"✅ 乗車情報を登録しました！\n\n"
            f"🚇 {train_id}　{car_number}号車　{seat_number}\n\n"
            f"マッチングをお待ちください。"
        )
    )


def reply_error() -> TextSendMessage:
    return TextSendMessage(
        text="❌ 登録に失敗しました。しばらく経ってから再度お試しください。"
    )


def reply_default() -> TextSendMessage:
    return TextSendMessage(
        text='メニューから「乗車情報登録」を選択するか、「登録」と入力してください。'
    )


def reply_cancelled() -> TextSendMessage:
    return TextSendMessage(text="❌ 登録をキャンセルしました。")
