# LINE サポーターbot

横浜市営地下鉄のサポーター（席を譲る人）とテイカー（席に座りたい人）をマッチングする LINE ボットです。

---

## 機能一覧

| トリガーワード | 機能 | 対象 |
|--------------|------|------|
| 「登録」 | 乗車情報登録 | サポーター |
| 「依頼確認」 | 受理できる依頼の一覧を確認 | サポーター |
| 「号車を探す」 | サポーターが多い号車を検索 | テイカー |
| 「座席リクエスト」 | 同じ号車のサポーターに依頼を送信 | テイカー |
| 「キャンセル」 | 操作を中断 | 共通 |

---

## 各機能のフロー

### 乗車情報登録（サポーター）
```
「登録」と送信
  → 列車番号を入力（例：A0002）
  → 号車を選択（1〜6号車）
  → 座席の列を選択（A〜E）
  → 座席番号を入力（例：12）
  → 確認画面 → 「✅ 登録する」
  → 登録完了
```

### 候補問い合わせ（テイカー）
```
「号車を探す」と送信
  → 列車番号を入力
  → サポーターが最も多い号車番号を返答
```

### 座席リクエスト（テイカー）
```
「座席リクエスト」と送信
  → 列車番号を入力
  → 号車を選択
  → 同じ号車のサポーターに依頼を送信
```

### 依頼確認・受理（サポーター）
```
「依頼確認」と送信
  → 受理できる依頼の一覧を表示
  → 「依頼 #XX」を選択
  → 受理完了（※後述の残タスクを参照）
```

### プッシュ通知（自動）
ボットが5秒ごとにバックエンドを確認し、新着があれば自動で通知します。

| 通知の種類 | 内容 |
|-----------|------|
| `give` | 「同じ電車に席に座りたい人がいます」 |
| `thanks` | 「席を譲った人からお礼が届きました」 |

---

## ファイル構成

```
LINE_supporter_bot/
├── main.py            # ボットのメイン処理（LINEからメッセージを受け取る）
├── messages.py        # LINEに送るメッセージの定義（クイックリプライ等）
├── api_client.py      # バックエンドAPIにデータを送る処理
├── setup_rich_menu.py # LINEのリッチメニュー（下部メニュー）を作成するスクリプト
├── requirements.txt   # 必要なPythonライブラリ一覧
├── .env               # 秘密情報（トークン等）※GitHubには上げない
└── .env.example       # .envのテンプレート（GitHubに上げてOK）
```

---

## 仕組み

```
LINEユーザー
  ↓ メッセージ送信
LINE サーバー
  ↓ Webhook（自動転送）
ngrok（HTTPS化）
  ↓
uvicorn + FastAPI（このボット）
  ↓ APIを呼び出す
バックエンドAPI（https://100v9train.f5.si）
  ↓
MySQL データベース
```

---

## セットアップ手順（初回のみ）

### 1. リポジトリを clone する

```bash
git clone https://github.com/100pro-train-seat/LINE_supporter_bot.git
cd LINE_supporter_bot
```

### 2. Python の仮想環境を作る

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 必要なライブラリをインストールする

```bash
pip install fastapi uvicorn python-dotenv httpx future "requests==2.31.0"
pip install line-bot-sdk==2.4.3 --no-deps
pip install "aiohttp>=3.9.0"
```

### 4. 環境変数を設定する

```bash
cp .env.example .env
nano .env   # 各項目を実際の値に書き換える
```

`.env` の内容：

| 変数名 | 説明 |
|--------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE公式アカウントの管理画面から取得 |
| `LINE_CHANNEL_SECRET` | LINE公式アカウントの管理画面から取得 |
| `BACKEND_API_URL` | バックエンドAPIのURL |
| `BACKEND_API_TOKEN` | 内部API用トークン（バックエンド担当から取得） |

nano の保存方法：`Ctrl+X` → `Y` → `Enter`

---

## 起動方法（VPS上で常時動かす）

```bash
cd ~/LINE_supporter_bot
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
nohup ngrok http --url=heavenly-nonvascularly-georgianne.ngrok-free.dev 8000 &
```

### ログを確認する

```bash
cat ~/LINE_supporter_bot/nohup.out
```

---

## LINE Developers の設定

1. `https://developers.line.biz/console/` を開く
2. チャンネル → **Messaging API** タブ
3. **Webhook URL** に以下を設定：

```
https://heavenly-nonvascularly-georgianne.ngrok-free.dev/webhook
```

4. **Update** → **Verify** で成功すれば OK

---

## VPS が再起動した場合

```bash
ssh train@160.251.236.85
cd ~/LINE_supporter_bot
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
nohup ngrok http --url=heavenly-nonvascularly-georgianne.ngrok-free.dev 8000 &
```

---

## 現在の状況

| 機能 | 状態 |
|------|------|
| 乗車情報登録（サポーター） | ✅ 動作中 |
| 候補問い合わせ（テイカー） | ✅ 動作中 |
| 座席リクエスト（テイカー） | ✅ 動作中 |
| 依頼確認（サポーター） | ✅ 動作中 |
| プッシュ通知（give / thanks） | ✅ 動作中 |
| 依頼受理後のマッチング確定 | ⏳ バックエンド待ち |

---

## 残タスク

### 依頼受理のAPI（バックエンドチームへの依頼）

現在「依頼 #XX」を押してもマッチングが確定しません。バックエンドに以下のAPIを作ってもらう必要があります。

> **`POST /match/accept`**
> - リクエスト：`asking_id`（依頼ID）、`Authorization: Bearer <トークン>`
> - 処理：サポーターとテイカーのステータスを「マッチング中」に更新、待機情報を削除
> - レスポンス：`{"ok": true, "code": 201, "taker_line_user_id": "Uxxxxxxxxxx"}`
>
> ※ レスポンスに `taker_line_user_id` を含めることで、LINE Bot 側からテイカーにも通知を送れます。

APIができたら `main.py` の `# TODO` 部分にすぐ実装できます。

---

## 関係するサービス

| サービス | URL / 情報 |
|----------|-----------|
| LINE Developers | https://developers.line.biz/console/ |
| バックエンドAPI | https://100v9train.f5.si |
| VPS | 160.251.236.85 |
| ngrok ダッシュボード | https://dashboard.ngrok.com |
| GitHubリポジトリ | https://github.com/100pro-train-seat/LINE_supporter_bot |
