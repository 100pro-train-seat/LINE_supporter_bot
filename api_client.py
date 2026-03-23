import logging
import os

import httpx

logger = logging.getLogger(__name__)

BASE_URL       = os.getenv("BACKEND_API_URL",   "https://100v9train.f5.si")
INTERNAL_TOKEN = os.getenv("BACKEND_API_TOKEN", "")


def _request(method: str, path: str, token: str = "", **kwargs):
    """HTTPリクエストを送り、レスポンスのJSONを返す。失敗時は None。"""
    headers = {"Authorization": f"Bearer {token or INTERNAL_TOKEN}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = getattr(client, method)(f"{BASE_URL}{path}", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("%s %s failed: %s", method.upper(), path, exc)
        return None


def _login(line_user_id: str) -> str:
    """LINE user ID でログインしてトークンを取得する。失敗時は空文字を返す。"""
    result = _request("post", "/account/login/id", data={"line_user_id": line_user_id})
    return result.get("token", "") if result else ""


def register_supporter_seat(*, line_user_id: str, train_id: str, car_number: str, seat_number: str) -> bool:
    """サポーターの乗車情報をバックエンドAPIに登録する。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("post", "/seat/register", token,
                      data={"train_id": train_id, "car_number": car_number, "seat_number": seat_number})
    return result is not None


def find_most_supporter_car(*, line_user_id: str, train_id: str) -> int | None:
    """指定した列車でサポーターが最も多い号車番号を返す。いない場合は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/seat/most", token, params={"train_id": train_id})
    return result.get("car_number") if result else None


def send_seat_request(*, line_user_id: str, train_id: str, car_number: str) -> bool:
    """テイカーが座席リクエストを送信する。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("post", "/match/ask", token,
                      data={"train_id": train_id, "car_number": car_number})
    return result is not None


def get_match_list(*, line_user_id: str) -> list | None:
    """サポーターが受理可能な依頼IDの一覧を取得する。エラー時は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/match/list", token)
    return result.get("asking") if result else None


def get_internal_messages() -> list:
    """バックエンドから新着メッセージ一覧を取得する。"""
    result = _request("get", "/internal/messages")
    return result.get("messages", []) if result else []
