import logging
import os

import httpx

logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.getenv("BACKEND_API_URL", "https://100v9train.f5.si")


def _login(line_user_id: str) -> str:
    """LINE user ID でログインしてトークンを取得する。失敗時は空文字を返す。"""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{BACKEND_BASE_URL}/account/login/id",
                data={"line_user_id": line_user_id},
            )
        response.raise_for_status()
        token = response.json().get("token", "")
        if token:
            logger.info("Login successful for user: %s", line_user_id)
            return token
        logger.error("Login returned empty token for user: %s", line_user_id)
    except Exception as exc:
        logger.error("Login failed for user %s: %s", line_user_id, exc)
    return ""


def register_supporter_seat(*, line_user_id: str, train_id: str, car_number: str, seat_number: str) -> bool:
    """サポーターの乗車情報をバックエンドAPIに登録する。"""
    token = _login(line_user_id)
    if not token:
        return False
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{BACKEND_BASE_URL}/seat/register",
                data={"train_id": train_id, "car_number": car_number, "seat_number": seat_number},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        logger.info("Seat registered – user=%s train=%s car=%s seat=%s", line_user_id, train_id, car_number, seat_number)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error("Register API error %s: %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.error("Failed to register seat: %s", exc)
    return False


def find_most_supporter_car(*, line_user_id: str, train_id: str) -> int | None:
    """指定した列車でサポーターが最も多い号車番号を返す。いない場合は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{BACKEND_BASE_URL}/seat/most",
                params={"train_id": train_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        car_number = response.json().get("car_number")
        logger.info("Most supporter car – train=%s car=%s", train_id, car_number)
        return car_number
    except httpx.HTTPStatusError as exc:
        logger.error("Find car API error %s: %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.error("Failed to find most supporter car: %s", exc)
    return None


def send_seat_request(*, line_user_id: str, train_id: str, car_number: str) -> bool:
    """テイカーが座席リクエストを送信する。"""
    token = _login(line_user_id)
    if not token:
        return False
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{BACKEND_BASE_URL}/match/ask",
                data={"train_id": train_id, "car_number": car_number},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        logger.info("Seat request sent – user=%s train=%s car=%s", line_user_id, train_id, car_number)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error("Seat request API error %s: %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.error("Failed to send seat request: %s", exc)
    return False


def get_match_list(*, line_user_id: str) -> list | None:
    """サポーターが受理可能な依頼IDの一覧を取得する。エラー時は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{BACKEND_BASE_URL}/match/list",
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        asking = response.json().get("asking", [])
        logger.info("Match list – user=%s asking=%s", line_user_id, asking)
        return asking
    except httpx.HTTPStatusError as exc:
        logger.error("Match list API error %s: %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.error("Failed to get match list: %s", exc)
    return None
