from __future__ import annotations

import uuid
from typing import Set


class SessionManager:
    """Simple session lifecycle manager."""

    def __init__(self) -> None:
        self._sessions: Set[str] = set()

    def create(self) -> str:
        sid = uuid.uuid4().hex
        self._sessions.add(sid)
        return sid

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def delete(self, session_id: str) -> None:
        self._sessions.discard(session_id)


_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager

