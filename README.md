# LINE サポーターbot（乗車情報登録）

横浜市営地下鉄のサポーターが乗車情報（列車・号車・座席）を LINE から登録するボットです。

---

## どんなことができる？

LINE でサポーターが以下の流れで座席を登録できます。

```
「登録」と送信
  → 列車IDを入力（例：A0002）
  → 号車を選択（1〜6号車）
  → 座席の列を選択（A〜E）
  → 座席の番号を入力（例：12）
  → 確認画面（「✅ 登録する」/「🔄 やり直す」）
  → バックエンドAPIに送信して完了！
```

---

## ファイル構成

```
LINE_supporter_bot/
├── main.py            # ボットのメイン処理（LINEからメッセージを受け取る）
├── messages.py        # LINEに送るメッセージの定義（クイックリプライ等）
├── session.py         # ユーザーごとの会話の状態を管理する
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
  ↓ 登録データを送信
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
pip install fastapi uvicorn python-dotenv httpx paramiko future "requests==2.31.0"
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
| `BACKEND_API_TOKEN` | バックエンドAPIの認証トークン |
| `VPS_HOST` | VPSのIPアドレス |
| `VPS_USER` | VPSのSSHユーザー名 |
| `VPS_PASS` | VPSのSSHパスワード |
| `DB_USER` | MySQLのユーザー名 |
| `DB_PASS` | MySQLのパスワード |
| `DB_NAME` | MySQLのデータベース名 |
| `BOT_LINE_USER_ID` | BOTアカウントのLINEユーザーID |

nano の保存方法：`Ctrl+X` → `Y` → `Enter`

---

## 起動方法（VPS上で常時動かす）

### uvicorn をバックグラウンドで起動

```bash
cd ~/LINE_supporter_bot
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```

### ngrok をバックグラウンドで起動

```bash
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

uvicorn と ngrok が止まるので、以下を実行して再起動します：

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
| LINEでの会話フロー | ✅ 動作中 |
| VPSへのデプロイ | ✅ 完了 |
| 24時間稼働 | ✅ Mac不要 |
| バックエンドAPIへの登録 | ❌ 500エラー（バックエンド側の調査が必要） |

### 500エラーについて

`POST https://100v9train.f5.si/api/supporters/seats` に以下のフォームデータを送ると 500 エラーが返ってくる：

```
train_id=A0001
car_number=3
seat_number=A12
```

バックエンド担当者にサーバー側のエラーログを確認してもらう必要があります。

---

## 関係するサービス

| サービス | URL / 情報 |
|----------|-----------|
| LINE Developers | https://developers.line.biz/console/ |
| バックエンドAPI | https://100v9train.f5.si |
| VPS | 160.251.236.85 |
| ngrok ダッシュボード | https://dashboard.ngrok.com |
| GitHubリポジトリ | https://github.com/100pro-train-seat/LINE_supporter_bot |
