from linebot.models import (
    BoxComponent,
    BubbleContainer,
    FlexSendMessage,
    ImageSendMessage,
    MessageAction,
    QuickReply,
    QuickReplyButton,
    SeparatorComponent,
    TextComponent,
    TextSendMessage,
)

SEAT_MAP_URL = "https://heavenly-nonvascularly-georgianne.ngrok-free.dev/static/trainmap.png"

SEAT_POSITIONS = {
    "A": "端席（右端）",
    "B": "ドア横（右ブロック）",
    "C": "ドア間（右中央）",
    "D": "ドア横（右内側）",
    "E": "ドア横（左内側）",
    "F": "ドア間（左中央）",
    "G": "ドア横（左ブロック）",
    "H": "端席（左端）",
}
VALID_SEAT_POSITIONS = set(SEAT_POSITIONS.keys())


def _btn(label: str, text: str) -> QuickReplyButton:
    return QuickReplyButton(action=MessageAction(label=label, text=text))


# ── サポーター用 ──────────────────────────────────────────────────

def ask_train_id() -> TextSendMessage:
    return TextSendMessage(text="🚇 乗車する列車番号を入力してください\n（例：3000A）")


def ask_carriage() -> TextSendMessage:
    items = [_btn(f"{i}号車", str(i)) for i in range(1, 7)]
    return TextSendMessage(text="🚃 何号車ですか？", quick_reply=QuickReply(items=items))


def ask_seat_position() -> list:
    items = [_btn(k, k) for k in SEAT_POSITIONS.keys()]
    return [
        ImageSendMessage(
            original_content_url=SEAT_MAP_URL,
            preview_image_url=SEAT_MAP_URL,
        ),
        TextSendMessage(text="💺 座席の位置を選んでください", quick_reply=QuickReply(items=items)),
    ]


def ask_confirm(session: dict) -> TextSendMessage:
    pos = session["seat_number"]
    body = (
        f"📋 以下の内容で登録しますか？\n\n"
        f"🚇 列車番号：{session['train_id']}\n"
        f"🚃 号車：{session['car_number']}号車\n"
        f"💺 位置：{pos}（{SEAT_POSITIONS[pos]}）"
    )
    items = [_btn("✅ 登録する", "✅ 登録する"), _btn("🔄 やり直す", "🔄 やり直す")]
    return TextSendMessage(text=body, quick_reply=QuickReply(items=items))


def reply_success(session: dict) -> TextSendMessage:
    pos = session["seat_number"]
    return TextSendMessage(
        text=f"✅ 乗車情報を登録しました！\n\n🚇 {session['train_id']}　{session['car_number']}号車　{pos}（{SEAT_POSITIONS[pos]}）"
    )


def reply_match_list(asking_ids: list) -> TextSendMessage:
    items = [_btn(f"依頼 #{asking_id}", f"受理する {asking_id}") for asking_id in asking_ids]
    return TextSendMessage(
        text=f"📋 受理できる依頼が {len(asking_ids)} 件あります。\n受理する依頼を選んでください。",
        quick_reply=QuickReply(items=items),
    )


def reply_match_empty() -> TextSendMessage:
    return TextSendMessage(text="現在、受理できる依頼はありません。")


def reply_match_accepted() -> TextSendMessage:
    return TextSendMessage(text="✅ 依頼を受理しました。\nマッチングが成立したらお知らせします。")


# ── テイカー用 ────────────────────────────────────────────────────

def ask_taker_train_id() -> TextSendMessage:
    return TextSendMessage(text="🔍 乗車する列車番号を入力してください\n（例：3000A）")


def ask_request_carriage() -> TextSendMessage:
    items = [_btn(f"{i}号車", str(i)) for i in range(1, 7)]
    return TextSendMessage(text="🚃 乗車している号車を選んでください", quick_reply=QuickReply(items=items))


def reply_taker_result(train_id: str, car_number: int) -> TextSendMessage:
    return TextSendMessage(
        text=f"✅ 乗車状況を確認しました！\n\n🚇 列車番号：{train_id}\n🚃 {car_number}号車 がおすすめです"
    )


def reply_taker_not_found(train_id: str) -> TextSendMessage:
    return TextSendMessage(
        text=f"😔 列車番号：{train_id} に\n席を譲れるサポーターが見つかりませんでした。\n\nしばらく経ってから再度お試しください。"
    )


def reply_request_sent() -> TextSendMessage:
    return TextSendMessage(text="✅ 座席リクエストを送信しました。\nサポーターからの返答をお待ちください。")


# ── プッシュ通知 ──────────────────────────────────────────────────

def push_give() -> TextSendMessage:
    return TextSendMessage(text="🚃 同じ電車に席に座りたい人がいます。\n「依頼確認」で依頼を確認してください。")


def push_thanks() -> TextSendMessage:
    return TextSendMessage(text="🙏 先ほど席を譲った人からお礼が届きました。\nありがとうございました！")


# ── ランク ────────────────────────────────────────────────────────

# (matched_count の閾値, ランク名, 絵文字アイコン)
_RANKS = [
    (11, "レジェンド", "👑"),
    (8,  "ヒーロー",   "🛡️"),
    (5,  "パートナー", "🤝"),
    (2,  "ひよこ",     "🐦"),
    (0,  "たまご",     "🥚"),
]


def _get_rank(matched_count: int) -> tuple[str, str]:
    for threshold, name, icon in _RANKS:
        if matched_count >= threshold:
            return name, icon
    return "たまご", "🥚"


def reply_rank(matched_count: int, point: int) -> FlexSendMessage:
    rank_name, icon = _get_rank(matched_count)
    bubble = BubbleContainer(
        body=BoxComponent(
            layout="vertical",
            spacing="md",
            contents=[
                TextComponent(text="🏅 サポーターランク", weight="bold", color="#888888", size="sm"),
                TextComponent(text=icon, size="5xl", align="center"),
                TextComponent(text=rank_name, weight="bold", size="xxl", align="center"),
                SeparatorComponent(margin="md"),
                BoxComponent(
                    layout="horizontal",
                    margin="md",
                    contents=[
                        TextComponent(text="席を譲った回数", color="#555555", flex=1),
                        TextComponent(text=f"{matched_count} 回", weight="bold", flex=1, align="end"),
                    ],
                ),
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        TextComponent(text="保有ポイント", color="#555555", flex=1),
                        TextComponent(text=f"{point} pt", weight="bold", flex=1, align="end"),
                    ],
                ),
            ],
        )
    )
    return FlexSendMessage(alt_text=f"ランク: {rank_name} | {matched_count}回 | {point}pt", contents=bubble)


# ── 共通 ──────────────────────────────────────────────────────────

def reply_default() -> TextSendMessage:
    return TextSendMessage(text='メニューから機能を選択するか、「登録」または「席を探す」と入力してください。')


def reply_cancelled() -> TextSendMessage:
    return TextSendMessage(text="❌ キャンセルしました。")
