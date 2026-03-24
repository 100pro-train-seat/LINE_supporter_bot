"""
LINE Rich Menu タブ切り替えセットアップスクリプト

初回のみ実行してください。

使い方:
    python setup_rich_menu.py

事前準備:
    .env に LINE_CHANNEL_ACCESS_TOKEN を設定する。
    rich_menu_tab1.png（2500×843px）: 「席をゆずる」タブがアクティブな画像
    rich_menu_tab2.png（2500×843px）: 「席にすわりたい」タブがアクティブな画像

レイアウト（小サイズ 2500×843）:
    ┌──────────────────┬──────────────────┐ ← タブ行（高さ150px）
    │  席をゆずる       │  席にすわりたい   │
    ├──────────────────┼──────────────────┤ ← ボタン行（高さ693px）
    │  乗車位置登録     │  ランクを確認     │ （タブ1）
    │  乗車情報問い合わせ│  座席リクエスト   │ （タブ2）
    └──────────────────┴──────────────────┘
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

ALIAS_TAB1 = "richmenu-alias-supporter"
ALIAS_TAB2 = "richmenu-alias-taker"

# タブ行の高さ
TAB_H    = 150
# ボタン行の高さ（843 - 150）
BUTTON_H = 693

# タブ1（席をゆずる）のメニュー定義
MENU_TAB1 = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "席をゆずる",
    "chatBarText": "メニューを開く",
    "areas": [
        {
            # タブ1ヘッダー（タップ不可のためポストバックで無視）
            "bounds": {"x": 0, "y": 0, "width": 1250, "height": TAB_H},
            "action": {"type": "postback", "label": "席をゆずる", "data": "tab=supporter"},
        },
        {
            # タブ2ヘッダー → タブ2に切り替え
            "bounds": {"x": 1250, "y": 0, "width": 1250, "height": TAB_H},
            "action": {"type": "richmenuswitch", "richMenuAliasId": ALIAS_TAB2, "data": "tab=taker"},
        },
        {
            # 乗車位置登録
            "bounds": {"x": 0, "y": TAB_H, "width": 1250, "height": BUTTON_H},
            "action": {"type": "message", "label": "乗車位置登録", "text": "登録"},
        },
        {
            # ランクを確認
            "bounds": {"x": 1250, "y": TAB_H, "width": 1250, "height": BUTTON_H},
            "action": {"type": "message", "label": "ランクを確認", "text": "ランクを確認する"},
        },
    ],
}

# タブ2（席にすわりたい）のメニュー定義
MENU_TAB2 = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "席にすわりたい",
    "chatBarText": "メニューを開く",
    "areas": [
        {
            # タブ1ヘッダー → タブ1に切り替え
            "bounds": {"x": 0, "y": 0, "width": 1250, "height": TAB_H},
            "action": {"type": "richmenuswitch", "richMenuAliasId": ALIAS_TAB1, "data": "tab=supporter"},
        },
        {
            # タブ2ヘッダー（タップ不可のためポストバックで無視）
            "bounds": {"x": 1250, "y": 0, "width": 1250, "height": TAB_H},
            "action": {"type": "postback", "label": "席にすわりたい", "data": "tab=taker"},
        },
        {
            # 乗車情報問い合わせ
            "bounds": {"x": 0, "y": TAB_H, "width": 1250, "height": BUTTON_H},
            "action": {"type": "message", "label": "乗車情報問い合わせ", "text": "号車を探す"},
        },
        {
            # 座席リクエスト
            "bounds": {"x": 1250, "y": TAB_H, "width": 1250, "height": BUTTON_H},
            "action": {"type": "message", "label": "座席リクエスト", "text": "座席リクエスト"},
        },
    ],
}


def create_rich_menu(body: dict, label: str) -> str:
    res = requests.post(f"{BASE}/richmenu", headers=HEADERS_JSON, json=body)
    res.raise_for_status()
    menu_id: str = res.json()["richMenuId"]
    print(f"✅ リッチメニュー作成完了（{label}）: {menu_id}")
    return menu_id


def upload_image(menu_id: str, image_path: str, label: str) -> bool:
    if not os.path.exists(image_path):
        print(f"⚠️  {image_path} が見つかりません。スキップします。")
        return False
    with open(image_path, "rb") as f:
        res = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{menu_id}/content",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "image/png"},
            data=f.read(),
        )
    res.raise_for_status()
    print(f"✅ 画像アップロード完了（{label}）")
    return True


def create_alias(menu_id: str, alias_id: str) -> None:
    # 既存のエイリアスを削除してから作成
    requests.delete(f"{BASE}/richmenuAlias/{alias_id}", headers=HEADERS_JSON)
    res = requests.post(
        f"{BASE}/richmenuAlias",
        headers=HEADERS_JSON,
        json={"richMenuAliasId": alias_id, "richMenuId": menu_id},
    )
    res.raise_for_status()
    print(f"✅ エイリアス作成完了: {alias_id}")


def set_default(menu_id: str) -> None:
    res = requests.post(f"{BASE}/user/all/richmenu/{menu_id}", headers=HEADERS_JSON)
    res.raise_for_status()
    print("✅ デフォルトリッチメニューに設定しました（タブ1）")


def main() -> None:
    # 2つのメニューを作成
    id1 = create_rich_menu(MENU_TAB1, "席をゆずる")
    id2 = create_rich_menu(MENU_TAB2, "席にすわりたい")

    # 画像をアップロード
    upload_image(id1, "rich_menu_tab1.png", "席をゆずる")
    upload_image(id2, "rich_menu_tab2.png", "席にすわりたい")

    # エイリアスを作成（タブ切り替えに必要）
    create_alias(id1, ALIAS_TAB1)
    create_alias(id2, ALIAS_TAB2)

    # タブ1をデフォルトに設定
    set_default(id1)

    print(f"\n🎉 セットアップ完了！")
    print(f"  タブ1（席をゆずる）    ID: {id1}")
    print(f"  タブ2（席にすわりたい） ID: {id2}")


if __name__ == "__main__":
    main()
