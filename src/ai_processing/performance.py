"""
Performance Optimization for AI Processing (Story 3-6)

Adds simple rate limiting and in-memory caching for LLM calls.
"""

import time
import hashlib
from typing import Optional, Dict, Any
from collections import deque


class AICache:
    def __init__(self, ttl_seconds: int = 900, max_items: int = 1000):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, Any] = {}
        self._order: deque[str] = deque()

    def _key(self, prompt: str, model: str) -> str:
        return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[str]:
        k = self._key(prompt, model)
        item = self._store.get(k)
        if not item:
            return None
        if time.time() - item["ts"] > self.ttl:
            self._store.pop(k, None)
            return None
        return item["value"]

    def set(self, prompt: str, model: str, value: str):
        k = self._key(prompt, model)
        self._store[k] = {"value": value, "ts": time.time()}
        self._order.append(k)
        while len(self._order) > self.max_items:
            old = self._order.popleft()
            self._store.pop(old, None)


class RateLimiter:
    def __init__(self, max_calls: int = 60, per_seconds: int = 60):
        self.max_calls = max_calls
        self.per = per_seconds
        self._calls: deque[float] = deque()

    def allow(self) -> bool:
        now = time.time()
        # Remove old calls
        while self._calls and now - self._calls[0] > self.per:
            self._calls.popleft()
        if len(self._calls) < self.max_calls:
            self._calls.append(now)
            return True
        return False

