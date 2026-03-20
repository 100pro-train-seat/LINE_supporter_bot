"""In-memory session manager for tracking user conversation state."""
from typing import Any, Dict, Optional


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(user_id)

    def set(self, user_id: str, data: Dict[str, Any]) -> None:
        self._sessions[user_id] = data

    def update(self, user_id: str, **kwargs: Any) -> None:
        if user_id in self._sessions:
            self._sessions[user_id].update(kwargs)

    def delete(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)
