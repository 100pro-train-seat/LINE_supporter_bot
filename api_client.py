import logging
import os

import httpx

logger = logging.getLogger(__name__)

BASE_URL       = os.getenv("BACKEND_API_URL",   "https://100v9train.f5.si")
INTERNAL_TOKEN = os.getenv("BACKEND_API_TOKEN", "")

_last_error: str = "エラーが発生しました。"


def get_last_error() -> str:
    return _last_error


def _request(method: str, path: str, token: str = "", **kwargs):
    """HTTPリクエストを送り、レスポンスのJSONを返す。失敗時は None。"""
    global _last_error
    headers = {"Authorization": f"Bearer {token or INTERNAL_TOKEN}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = getattr(client, method)(f"{BASE_URL}{path}", headers=headers, **kwargs)
        try:
            data = response.json()
        except Exception:
            _last_error = f"サーバーエラーが発生しました。（{response.status_code}）"
            logger.error("%s %s error(%s): empty or invalid response body", method.upper(), path, response.status_code)
            return None
        if not response.is_success or not data.get("ok", True):
            _last_error = data.get("error", "エラーが発生しました。")
            logger.error("%s %s error(%s): %s", method.upper(), path, response.status_code, _last_error)
            return None
        return data
    except Exception as exc:
        _last_error = "通信エラーが発生しました。"
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


def accept_match(*, line_user_id: str, match_id: str) -> bool:
    """サポーターが依頼に立候補する。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("post", "/match/candidate", token, data={"match_id": match_id})
    return result is not None


def get_matched(*, line_user_id: str) -> dict | None:
    """テイカーのマッチング結果を取得する。未マッチの場合は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/match/matched", token)
    return result if result else None


def get_internal_messages() -> list:
    """メッセージキューからすべての通知を取得する。"""
    result = _request("get", "/internal/messages")
    return result.get("messages", []) if result else []


def complete_match(*, line_user_id: str) -> bool:
    """テイカーがマッチングを完了し、サポーターにthanks通知を送る。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("post", "/match/thanks", token)
    return result is not None


def cancel_match_request(*, line_user_id: str) -> bool:
    """依頼者がリクエストをキャンセルする。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("delete", "/match/cancel", token)
    return result is not None


def delete_supporter_seat(*, line_user_id: str) -> bool:
    """サポーターが座席情報を削除する。"""
    token = _login(line_user_id)
    if not token:
        return False
    result = _request("delete", "/seat/delete", token)
    return result is not None


def get_user_profile(*, line_user_id: str) -> dict | None:
    """ユーザーの matched_count と point を取得する。エラー時は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/user/profile", token)
    return result if result else None


def search_stations(*, line_user_id: str, keyword: str) -> list | None:
    """駅名キーワードで駅を検索する。エラー時は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/timetable/search", token, params={"keyword": keyword})
    return result.get("stations") if result else None


def get_trains(*, line_user_id: str, station_id: int) -> list | None:
    """指定駅の直近5本の列車を取得する。エラー時は None。"""
    token = _login(line_user_id)
    if not token:
        return None
    result = _request("get", "/timetable/trains", token, params={"station_id": station_id})
    return result.get("trains") if result else None
