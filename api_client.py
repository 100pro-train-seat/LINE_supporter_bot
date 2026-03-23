"""HTTP client for backend API (supporter seat registration).

トークンが期限切れ (401) の場合、/account/login/id に LINE user ID を送って
新しいトークンを取得し、自動でリトライする。
"""
import logging
import os
import threading

import httpx

logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.getenv("BACKEND_API_URL", "https://100v9train.f5.si")
BOT_LINE_USER_ID = os.getenv("BOT_LINE_USER_ID", "")

# トークンキャッシュ（スレッドセーフ）
_token: str = os.getenv("BACKEND_API_TOKEN", "")
_token_lock = threading.Lock()


def _get_token() -> str:
    with _token_lock:
        return _token


def _refresh_token() -> bool:
    """LINE user ID でログインして新しいトークンを取得する。"""
    global _token
    url = f"{BACKEND_BASE_URL}/account/login/id"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                data={"line_user_id": BOT_LINE_USER_ID},
            )
        response.raise_for_status()
        data = response.json()
        new_token = data.get("token", "")
        if new_token:
            with _token_lock:
                _token = new_token
            logger.info("Token refreshed via /account/login/id")
            return True
        logger.error("Token refresh returned empty token: %s", data)
    except Exception as exc:
        logger.error("Token refresh failed: %s", exc)
    return False


def register_supporter_seat(
    *,
    train_id: str,
    car_number: str,
    seat_number: str,
) -> bool:
    """サポーターの乗車情報をバックエンドAPIに登録する。

    401 (トークン期限切れ) の場合は自動でトークンを更新してリトライする。

    Args:
        train_id:    列車ID（例: A0002）
        car_number:  号車番号（例: 3）
        seat_number: 座席番号（例: A12）
    """
    url = f"{BACKEND_BASE_URL}/seat/register"
    payload = {
        "train_id":    train_id,
        "car_number":  car_number,
        "seat_number": seat_number,
    }

    for attempt in range(2):
        headers = {"Authorization": f"Bearer {_get_token()}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, data=payload, headers=headers)

            if response.status_code == 401:
                if attempt == 0:
                    logger.warning("Token expired (401). Refreshing token...")
                    if _refresh_token():
                        continue
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
