"""HTTP client for backend API (supporter seat registration).

サポーター本人の LINE user ID でログインしてトークンを取得し、
座席登録APIを呼び出す。
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.getenv("BACKEND_API_URL", "https://100v9train.f5.si")


def _login(line_user_id: str) -> str:
    """LINE user ID でログインしてトークンを取得する。失敗時は空文字を返す。"""
    url = f"{BACKEND_BASE_URL}/account/login/id"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data={"line_user_id": line_user_id})
        response.raise_for_status()
        token = response.json().get("token", "")
        if token:
            logger.info("Login successful for user: %s", line_user_id)
            return token
        logger.error("Login returned empty token for user: %s", line_user_id)
    except Exception as exc:
        logger.error("Login failed for user %s: %s", line_user_id, exc)
    return ""


def register_supporter_seat(
    *,
    line_user_id: str,
    train_id: str,
    car_number: str,
    seat_number: str,
) -> bool:
    """サポーターの乗車情報をバックエンドAPIに登録する。

    サポーター本人の LINE user ID でログインし、取得したトークンで登録する。

    Args:
        line_user_id: サポーターの LINE user ID
        train_id:     列車ID（例: A0002）
        car_number:   号車番号（例: 3）
        seat_number:  座席番号（例: A12）
    """
    token = _login(line_user_id)
    if not token:
        logger.error("Could not obtain token for user: %s", line_user_id)
        return False

    url = f"{BACKEND_BASE_URL}/seat/register"
    payload = {
        "train_id":    train_id,
        "car_number":  car_number,
        "seat_number": seat_number,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data=payload, headers=headers)
        response.raise_for_status()
        logger.info(
            "Seat registered – user=%s train=%s car=%s seat=%s",
            line_user_id, train_id, car_number, seat_number,
        )
        return True
    except httpx.HTTPStatusError as exc:
        logger.error("Register API error %s: %s", exc.response.status_code, exc.response.text)
        return False
    except Exception as exc:
        logger.error("Failed to register seat: %s", exc)
        return False
