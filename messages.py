from linebot.models import MessageAction, QuickReply, QuickReplyButton, TextSendMessage

SEAT_COLUMNS = ["A", "B", "C", "D", "E"]
VALID_SEAT_COLUMNS = set(SEAT_COLUMNS)


def _btn(label: str, text: str) -> QuickReplyButton:
    return QuickReplyButton(action=MessageAction(label=label, text=text))


# ── サポーター用 ──────────────────────────────────────────────────

def ask_train_id() -> TextSendMessage:
    return TextSendMessage(text="🚇 乗車する列車IDを入力してください\n（例：A0002）")


def ask_carriage() -> TextSendMessage:
    items = [_btn(f"{i}号車", str(i)) for i in range(1, 7)]
    return TextSendMessage(text="🚃 何号車ですか？", quick_reply=QuickReply(items=items))


def ask_seat_column() -> TextSendMessage:
    items = [_btn(col, col) for col in SEAT_COLUMNS]
    return TextSendMessage(text="💺 座席の列を選んでください\n（A〜E）", quick_reply=QuickReply(items=items))


def ask_seat_row() -> TextSendMessage:
    return TextSendMessage(text="🔢 座席の番号を入力してください\n（例：12）")


def ask_confirm(session: dict) -> TextSendMessage:
    body = (
        f"📋 以下の内容で登録しますか？\n\n"
        f"🚇 列車ID：{session['train_id']}\n"
        f"🚃 号車：{session['car_number']}号車\n"
        f"💺 座席：{session['seat_number']}"
    )
    items = [_btn("✅ 登録する", "✅ 登録する"), _btn("🔄 やり直す", "🔄 やり直す")]
    return TextSendMessage(text=body, quick_reply=QuickReply(items=items))


def reply_success(session: dict) -> TextSendMessage:
    return TextSendMessage(
        text=f"✅ 乗車情報を登録しました！\n\n🚇 {session['train_id']}　{session['car_number']}号車　{session['seat_number']}\n\nマッチングをお待ちください。"
    )


# ── テイカー用 ────────────────────────────────────────────────────

def ask_taker_train_id() -> TextSendMessage:
    return TextSendMessage(text="🔍 乗車する列車IDを入力してください\n（例：A0002）")


def reply_taker_result(train_id: str, car_number: int) -> TextSendMessage:
    return TextSendMessage(
        text=f"✅ 見つかりました！\n\n🚇 列車ID：{train_id}\n🚃 {car_number}号車 に乗ってください\n\nサポーターがお待ちしています。"
    )


def reply_taker_not_found(train_id: str) -> TextSendMessage:
    return TextSendMessage(
        text=f"😔 列車ID：{train_id} に\n席を譲れるサポーターが見つかりませんでした。\n\nしばらく経ってから再度お試しください。"
    )


# ── 共通 ──────────────────────────────────────────────────────────

def reply_error() -> TextSendMessage:
    return TextSendMessage(text="❌ 登録に失敗しました。しばらく経ってから再度お試しください。")


def reply_default() -> TextSendMessage:
    return TextSendMessage(text='メニューから機能を選択するか、「登録」または「席を探す」と入力してください。')


def reply_cancelled() -> TextSendMessage:
    return TextSendMessage(text="❌ キャンセルしました。")
