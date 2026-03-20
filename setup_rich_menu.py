"""
LINE Rich Menu セットアップスクリプト

サポーター用ボットのリッチメニューを作成・設定する。
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

BASE = "https://api.line.me/v2/bot"
HEADERS_JSON = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# リッチメニューのレイアウト定義（横2分割）
RICH_MENU_BODY = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "サポーターメニュー",
    "chatBarText": "メニューを開く",
    "areas": [
        {
            # 左側：乗車情報登録
            "bounds": {"x": 0, "y": 0, "width": 1250, "height": 843},
            "action": {"type": "message", "label": "乗車情報登録", "text": "乗車情報登録"},
        },
        {
            # 右側：ヘルプ
            "bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
            "action": {"type": "message", "label": "ヘルプ", "text": "ヘルプ"},
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
    print(f"✅ 画像アップロード完了")


def set_default(menu_id: str) -> None:
    res = requests.post(
        f"{BASE}/user/all/richmenu/{menu_id}",
        headers=HEADERS_JSON,
    )
    res.raise_for_status()
    print(f"✅ デフォルトリッチメニューに設定しました")


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
