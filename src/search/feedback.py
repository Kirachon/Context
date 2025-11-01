"""
Search Feedback Manager (Story 2.4)

Lightweight in-memory feedback system to adjust ranking quality over time.
"""
from __future__ import annotations

import math
import threading
from typing import Dict


class FeedbackManager:
    """In-memory feedback manager with simple score boosts by file path."""

    def __init__(self):
        self._lock = threading.Lock()
        self._upvotes: Dict[str, int] = {}
        self._downvotes: Dict[str, int] = {}

    def register_feedback(self, file_path: str, positive: bool) -> None:
        with self._lock:
            if positive:
                self._upvotes[file_path] = self._upvotes.get(file_path, 0) + 1
            else:
                self._downvotes[file_path] = self._downvotes.get(file_path, 0) + 1

    def get_score_boost(self, file_path: str) -> float:
        """
        Compute a bounded boost factor in [-1.0, +1.0] from feedback.
        Positive feedback increases the score; negative decreases it.
        """
        with self._lock:
            up = self._upvotes.get(file_path, 0)
            down = self._downvotes.get(file_path, 0)
        delta = up - down
        # Smoothly bound using tanh-like scaling
        # Scale: ~+/-0.76 at delta=2, ~+/-0.96 at delta=3, -> +/-1 as delta grows
        return math.tanh(delta / 2.0)

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {"upvotes": dict(self._upvotes), "downvotes": dict(self._downvotes)}


_feedback_manager: FeedbackManager | None = None


def get_feedback_manager() -> FeedbackManager:
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager

