"""
In-memory conversation state management.

Provides optional stateful multi-turn conversations keyed by conversation_id.
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from threading import Lock

from src.config.settings import settings


@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    conversation_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


class ConversationStateManager:
    """Thread-safe in-memory conversation state manager."""

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._lock = Lock()

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID, or None if not found."""
        with self._lock:
            self._cleanup_expired()
            conv = self._conversations.get(conversation_id)
            if conv:
                conv.last_accessed = time.time()
            return conv

    def create_conversation(self, conversation_id: str) -> Conversation:
        """Create a new conversation."""
        with self._lock:
            self._cleanup_expired()
            self._enforce_max_conversations()
            conv = Conversation(conversation_id=conversation_id)
            self._conversations[conversation_id] = conv
            return conv

    def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> Conversation:
        """Add a message to a conversation. Creates conversation if it doesn't exist."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                conv = Conversation(conversation_id=conversation_id)
                self._conversations[conversation_id] = conv

            # Enforce max messages per conversation
            max_msgs = getattr(
                settings, "conversation_max_messages_per_conversation", 100
            )
            if len(conv.messages) >= max_msgs:
                # Remove oldest message
                conv.messages.pop(0)

            conv.messages.append(ConversationMessage(role=role, content=content))
            conv.last_accessed = time.time()
            return conv

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation. Returns True if deleted, False if not found."""
        with self._lock:
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
                return True
            return False

    def _cleanup_expired(self):
        """Remove expired conversations (called with lock held)."""
        ttl = getattr(settings, "conversation_ttl_seconds", 3600)
        now = time.time()
        expired = [
            cid
            for cid, conv in self._conversations.items()
            if now - conv.last_accessed > ttl
        ]
        for cid in expired:
            del self._conversations[cid]

    def _enforce_max_conversations(self):
        """Remove oldest conversations if limit exceeded (called with lock held)."""
        max_convs = getattr(settings, "conversation_max_conversations", 1000)
        if len(self._conversations) >= max_convs:
            # Remove oldest by last_accessed
            sorted_convs = sorted(
                self._conversations.items(), key=lambda x: x[1].last_accessed
            )
            to_remove = len(self._conversations) - max_convs + 1
            for cid, _ in sorted_convs[:to_remove]:
                del self._conversations[cid]

    def get_stats(self) -> Dict[str, int]:
        """Get current state statistics."""
        with self._lock:
            return {
                "total_conversations": len(self._conversations),
                "total_messages": sum(
                    len(c.messages) for c in self._conversations.values()
                ),
            }


# Global singleton
_conversation_manager: Optional[ConversationStateManager] = None


def get_conversation_manager() -> ConversationStateManager:
    """Get the global conversation state manager singleton."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationStateManager()
    return _conversation_manager

