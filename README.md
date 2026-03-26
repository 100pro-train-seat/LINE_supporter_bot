# LINE サポーターbot

横浜市営地下鉄のサポーター（席を譲る人）と依頼者（席に座りたい人）をマッチングする LINE ボットです。

---

## 機能一覧

| トリガーワード | 機能 | 対象 |
|--------------|------|------|
| 「登録」 | 乗車情報登録 | サポーター |
| 「依頼確認」 | 受理できる依頼の一覧を確認 | サポーター |
| 「ランクを確認」 | サポーターランクと統計を確認 | サポーター |
| 「登録削除」 | 座席登録を削除 | サポーター |
| 「問い合わせ」 | サポーターが多い号車を検索 | 依頼者 |
| 「座席リクエスト」 | 同じ号車のサポーターに依頼を送信 | 依頼者 |
| 「✅ リクエスト完了」 | マッチング完了・サポーターにお礼を送信 | 依頼者 |
| 「リクエストキャンセル」 | 座席リクエストをキャンセル | 依頼者 |
| 「キャンセル」 | 操作を中断 | 共通 |

---

## 各機能のフロー

### 乗車情報登録（サポーター）
```
「登録」と送信
  → 列車番号を入力（例：3000A）
  → 号車を選択（1〜6号車）
  → 座席位置を選択（A〜H）
  → 確認画面 → 「✅ 登録する」
  → 登録完了
```

### 候補問い合わせ（依頼者）
```
「問い合わせ」と送信
  → 列車番号を入力
  → サポーターが最も多い号車番号を返答
```

### 座席リクエスト（依頼者）
```
「座席リクエスト」と送信
  → 列車番号を入力
  → 号車を選択
  → 同じ号車のサポーターに依頼を送信
  → マッチング成立時にプッシュ通知で自動お知らせ
```

### マッチング完了（依頼者）
```
マッチング成立通知に記載のサポーター情報を確認
  → 席を譲ってもらったら「✅ リクエスト完了」ボタンを押す
  → POST /match/thanks でマッチング完了
  → サポーターにお礼通知が届く
  → サポーターのポイント・レベルが上昇する
```

### 依頼確認・受理（サポーター）
```
「依頼確認」と送信
  → 受理できる依頼の一覧を表示
  → 「依頼 #XX」を選択
  → POST /match/candidate で立候補
  → 依頼者にマッチング成立通知が届く
```

### ランク確認（サポーター）
```
「ランクを確認」と送信
  → 席を譲った回数・保有ポイント・サポーターランクを表示
```

| ランク | 条件 |
|--------|------|
| 🥚 たまご | 0回〜 |
| 🐣 ひよこ | 2回〜 |
| 🤝 パートナー | 5回〜 |
| 🛡️ ヒーロー | 8回〜 |
| 👑 レジェンド | 11回〜 |

### キャンセル

| キーワード | 対象 | 動作 |
|-----------|------|------|
| 「リクエストキャンセル」 | 依頼者 | `DELETE /match/cancel` → サポーターにキャンセル通知 |
| 「登録削除」 | サポーター | `DELETE /seat/delete` → マッチ済みなら依頼者にキャンセル通知 |

### プッシュ通知（自動）
バックエンドでイベントが発生すると `messages` テーブルに挿入され、LINE Bot が5秒ごとに `GET /internal/messages` をポーリングして通知を送ります。

| 通知の種類 | 通知先 | タイミング |
|-----------|--------|-----------|
| `give` | サポーター | 依頼者が座席リクエストを送信したとき |
| `match` | 依頼者 | サポーターが立候補したとき |
| `thanks` | サポーター | 依頼者が「✅ リクエスト完了」を押したとき |
| `canceled` | 依頼者/サポーター | マッチがキャンセルされたとき |

---

## ファイル構成

```
LINE_supporter_bot/
├── main.py            # ボットのメイン処理（LINEからメッセージを受け取る）
├── messages.py        # LINEに送るメッセージの定義（クイックリプライ等）
├── api_client.py      # バックエンドAPIにデータを送る処理
├── setup_rich_menu.py # LINEのリッチメニュー（下部メニュー）を作成するスクリプト
├── static/            # 静的ファイル（trainmap.png 等）
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

【プッシュ通知の流れ】
バックエンド → messages テーブルに挿入
  ↑ LINE Bot が15秒ごとにポーリング（GET /internal/messages）
  ↓ 取得したメッセージをLINEにプッシュ通知
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
| 座席登録削除（サポーター） | ✅ 動作中 |
| 候補問い合わせ（依頼者） | ✅ 動作中 |
| 座席リクエスト（依頼者） | ✅ 動作中 |
| リクエストキャンセル（依頼者） | ✅ 動作中 |
| 依頼確認・立候補（サポーター） | ✅ 動作中 |
| ランク確認（サポーター） | ✅ 動作中 |
| マッチング完了・お礼送信（依頼者） | ✅ 動作中 |
| プッシュ通知 give（依頼リスト自動表示） | ✅ 動作中 |
| プッシュ通知 match（マッチング成立通知） | ✅ 動作中 |
| プッシュ通知 thanks（ランク表示付きお礼） | ✅ 動作中 |
| プッシュ通知 canceled（キャンセル通知） | ✅ 動作中 |

---

## 関係するサービス

| サービス | URL / 情報 |
|----------|-----------|
| LINE Developers | https://developers.line.biz/console/ |
| バックエンドAPI | https://100v9train.f5.si |
| VPS | 160.251.236.85 |
| ngrok ダッシュボード | https://dashboard.ngrok.com |
| GitHubリポジトリ | https://github.com/100pro-train-seat/LINE_supporter_bot |
