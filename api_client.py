"""HTTP client for backend API (supporter seat registration).

トークンが期限切れ (401) の場合、SSH 経由で VPS の MySQL に新しいトークンを
生成し、自動でリトライする。
"""
import logging
import os
import threading

import httpx
import paramiko

logger = logging.getLogger(__name__)

# ── バックエンドAPI ───────────────────────────────────────────────
BACKEND_BASE_URL = os.getenv("BACKEND_API_URL", "https://100v9train.f5.si")

# ── VPS / DB 接続情報（トークン自動更新用）──────────────────────
VPS_HOST         = os.getenv("VPS_HOST",         "160.251.236.85")
VPS_USER         = os.getenv("VPS_USER",         "train")
VPS_PASS         = os.getenv("VPS_PASS",         "train1234!")
DB_USER          = os.getenv("DB_USER",          "train")
DB_PASS          = os.getenv("DB_PASS",          "Train1234!")
DB_NAME          = os.getenv("DB_NAME",          "train")
BOT_LINE_USER_ID = os.getenv("BOT_LINE_USER_ID", "BOT_SUPPORTER_ACCOUNT")

# ── トークンキャッシュ（スレッドセーフ）─────────────────────────
_token: str = os.getenv("BACKEND_API_TOKEN", "")
_token_lock = threading.Lock()


def _get_token() -> str:
    with _token_lock:
        return _token


def _refresh_token() -> bool:
    """SSH 経由で VPS の MySQL に新しいトークンを生成し、メモリ上のトークンを更新する。"""
    global _token
    sql = (
        "SET @uid = (SELECT id FROM users WHERE line_user_id = '{bot_id}' LIMIT 1); "
        "INSERT INTO tokens (user_id, token, expired_at) "
        "  VALUES (@uid, HEX(RANDOM_BYTES(32)), DATE_ADD(NOW(), INTERVAL 1 DAY)); "
        "SELECT token FROM tokens ORDER BY id DESC LIMIT 1;"
    ).format(bot_id=BOT_LINE_USER_ID)

    cmd = f'mysql -u{DB_USER} -p{DB_PASS} {DB_NAME} -sN -e "{sql}"'

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=10)
        _, stdout, stderr = ssh.exec_command(cmd)
        lines = stdout.read().decode().strip().splitlines()
        ssh.close()

        new_token = lines[-1].strip() if lines else ""
        if new_token:
            with _token_lock:
                _token = new_token
            logger.info("Token refreshed via SSH+MySQL")
            return True

        logger.error("Token refresh returned empty. stderr: %s", stderr.read().decode())

    except Exception as exc:
        logger.error("Token refresh failed: %s", exc)

    return False


# ─────────────────────────────────────────────────────────────────
def register_supporter_seat(
    *,
    train_id: str,
    car_number: str,
    seat_number: str,
) -> bool:
    """サポーターの乗車情報をバックエンドAPIに登録する。

    401 (トークン期限切れ) を受け取った場合は自動でトークンを更新してリトライする。

    Args:
        train_id:    列車ID（例: A0002）
        car_number:  号車番号・数字のみ（例: 11）
        seat_number: 座席番号（例: A12）
    """
    url = f"{BACKEND_BASE_URL}/api/supporters/seats"
    payload = {
        "train_id":    train_id,
        "car_number":  car_number,
        "seat_number": seat_number,
    }

    for attempt in range(2):  # 最大2回試みる（1回目 → 401 → 更新 → 2回目）
        headers = {
            "Authorization": f"Bearer {_get_token()}",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                # application/x-www-form-urlencoded で送信
                response = client.post(url, data=payload, headers=headers)

            # トークン期限切れ → リフレッシュしてリトライ
            if response.status_code == 401:
                if attempt == 0:
                    logger.warning("Token expired (401). Refreshing token...")
                    if _refresh_token():
                        continue  # 新しいトークンでリトライ
                logger.error("Authentication failed after token refresh.")
                return False

            response.raise_for_status()
            logger.info(
                "Seat registered – train=%s car=%s seat=%s",
                train_id, car_number, seat_number,
            )
            return True

        except httpx.HTTPStatusError as exc:
            logger.error("Register API error %s: %s", exc.response.status_code, exc.response.text)
            return False
        except Exception as exc:
            logger.error("Failed to register seat: %s", exc)
            return False

    return False
