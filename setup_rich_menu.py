"""
LINE Rich Menu セットアップスクリプト

初回のみ実行してください。

使い方:
    python setup_rich_menu.py

事前準備:
    .env に LINE_CHANNEL_ACCESS_TOKEN を設定する。
    rich_menu.png（2500×843px）を同じディレクトリに置く。
    画像を用意できない場合は LINE Developers Console から手動でアップロード可能。
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
if not TOKEN:
    sys.exit("ERROR: LINE_CHANNEL_ACCESS_TOKEN が設定されていません。")

BASE         = "https://api.line.me/v2/bot"
HEADERS_JSON = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# リッチメニューのレイアウト定義（横3分割）
#
#  ┌──────────────┬──────────────┬──────────────┐
#  │  乗車状況    │  乗車状況    │  座席        │
#  │  を登録      │  問い合わせ  │  リクエスト  │
#  │ （サポーター）│ （テイカー） │ （テイカー） │
#  └──────────────┴──────────────┴──────────────┘
RICH_MENU_BODY = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "メインメニュー",
    "chatBarText": "メニューを開く",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
            "action": {"type": "message", "label": "乗車状況を登録", "text": "登録"},
        },
        {
            "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
            "action": {"type": "message", "label": "乗車状況問い合わせ", "text": "号車を探す"},
        },
        {
            "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
            "action": {"type": "message", "label": "座席リクエスト", "text": "座席リクエスト"},
        },
    ],
}


def create_rich_menu() -> str:
    res = requests.post(f"{BASE}/richmenu", headers=HEADERS_JSON, json=RICH_MENU_BODY)
    res.raise_for_status()
    menu_id: str = res.json()["richMenuId"]
    print(f"✅ リッチメニュー作成完了: {menu_id}")
    return menu_id


def upload_image(menu_id: str, image_path: str) -> None:
    with open(image_path, "rb") as f:
        res = requests.post(
            f"{BASE}/richmenu/{menu_id}/content",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "image/png"},
            data=f.read(),
        )
    res.raise_for_status()
    print("✅ 画像アップロード完了")


def set_default(menu_id: str) -> None:
    res = requests.post(f"{BASE}/user/all/richmenu/{menu_id}", headers=HEADERS_JSON)
    res.raise_for_status()
    print("✅ デフォルトリッチメニューに設定しました")


def main() -> None:
    menu_id = create_rich_menu()

    image_path = "rich_menu.png"
    if os.path.exists(image_path):
        upload_image(menu_id, image_path)
    else:
        print(
            f"⚠️  {image_path} が見つかりません。\n"
            "   LINE Developers Console > Messaging API > Rich menu から\n"
            f"   メニュー ID「{menu_id}」に画像を手動でアップロードしてください。"
        )

    set_default(menu_id)
    print(f"\n🎉 セットアップ完了！\nRich Menu ID: {menu_id}")


if __name__ == "__main__":
    main()
