"""
Conversation Manager for search/query context.

Thin wrapper around the global conversation state that exposes
lightweight helpers suitable for query refinement/enhancement flows.

Safe-by-default:
- Only used when feature flag `enable_conversation_tracking` is True.
- Gracefully handles absence of conversation state.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any

try:
    # Reuse the existing in-memory conversation manager
    from src.conversation.state import get_conversation_manager as _get_conv_mgr
except Exception:  # pragma: no cover - defensive fallback in environments without module
    _get_conv_mgr = None  # type: ignore

from src.config.settings import settings


class SearchConversationManager:
    """Lightweight adapter to read/write conversation context for queries."""

    def __init__(self):
        self._enabled = getattr(settings, "enable_conversation_tracking", False)

    @property
    def enabled(self) -> bool:
        return bool(self._enabled) and bool(getattr(settings, "conversation_state_enabled", True))

    def get_context(self, session_id: str, max_items: int = 5) -> List[str]:
        """Return a list of recent message contents for a session (oldest->newest).
        Returns an empty list if disabled or not found.
        """
        if not self.enabled or not session_id or _get_conv_mgr is None:
            return []
        mgr = _get_conv_mgr()
        conv = mgr.get_conversation(session_id)
        if not conv:
            return []
        msgs = [m.content for m in conv.messages][-max_items:]
        return msgs

    def add_user_query(self, session_id: str, query: str) -> None:
        """Append a user query message to the conversation (no-op if disabled)."""
        if not self.enabled or not session_id or _get_conv_mgr is None:
            return
        mgr = _get_conv_mgr()
        mgr.add_message(session_id, "user", query)

    def add_assistant_note(self, session_id: str, note: str) -> None:
        """Append an assistant note/snippet to the conversation (no-op if disabled)."""
        if not self.enabled or not session_id or _get_conv_mgr is None:
            return
        mgr = _get_conv_mgr()
        mgr.add_message(session_id, "assistant", note)

    def get_stats(self) -> Dict[str, Any]:
        """Surface minimal stats for diagnostics."""
        if _get_conv_mgr is None:
            return {"enabled": False}
        mgr = _get_conv_mgr()
        s = mgr.get_stats()
        return {"enabled": self.enabled, **s}

