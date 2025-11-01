"""
Query Cache (Story 5-1)

Simple in-memory TTL cache for query -> results payloads.
"""

import time
import hashlib
from typing import Any, Dict, Optional
from collections import deque


class QueryCache:
    def __init__(self, ttl_seconds: int = 600, max_items: int = 500):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, Any] = {}
        self._order: deque[str] = deque()

    def _key(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        import json
        parts = [query, json.dumps(filters or {}, sort_keys=True)]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def get(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        k = self._key(query, filters)
        item = self._store.get(k)
        if not item:
            return None
        if time.time() - item["ts"] > self.ttl:
            self._store.pop(k, None)
            return None
        return item["value"]

    def set(self, query: str, value: Dict[str, Any], filters: Optional[Dict[str, Any]] = None):
        k = self._key(query, filters)
        self._store[k] = {"value": value, "ts": time.time()}
        self._order.append(k)
        while len(self._order) > self.max_items:
            old = self._order.popleft()
            self._store.pop(old, None)


_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache

