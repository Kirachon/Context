from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List


@dataclass
class Message:
    role: str  # 'user' | 'assistant' | 'system'
    content: str


class ConversationTracker:
    """In-memory conversation tracker with a bounded history per session."""

    def __init__(self, max_history: int = 20) -> None:
        self._messages: Dict[str, Deque[Message]] = defaultdict(lambda: deque(maxlen=max_history))

    def add(self, session_id: str, role: str, content: str) -> None:
        self._messages[session_id].append(Message(role=role, content=content))

    def history(self, session_id: str) -> List[Dict[str, str]]:
        return [m.__dict__ for m in self._messages.get(session_id, deque())]


_tracker: ConversationTracker | None = None


def get_conversation_tracker() -> ConversationTracker:
    global _tracker
    if _tracker is None:
        _tracker = ConversationTracker()
    return _tracker

