"""
Query Cache (Story 5-1)

Simple in-memory TTL cache for query -> results payloads.
"""

import time
import hashlib
from typing import Any, Dict, Optional
from collections import deque
import threading


class QueryCache:
    def __init__(self, ttl_seconds: int = 600, max_items: int = 500):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, Any] = {}
        self._order: deque[str] = deque()
        self._lock = threading.Lock()

    def _key(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        import json

        parts = [query, json.dumps(filters or {}, sort_keys=True)]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def get(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        k = self._key(query, filters)
        with self._lock:
            item = self._store.get(k)
            if not item:
                return None
            if time.time() - item["ts"] > self.ttl:
                self._store.pop(k, None)
                return None
            return item["value"]

    def set(
        self,
        query: str,
        value: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ):
        k = self._key(query, filters)
        with self._lock:
            self._store[k] = {"value": value, "ts": time.time()}
            self._order.append(k)
            while len(self._order) > self.max_items:
                old = self._order.popleft()
                self._store.pop(old, None)


# Optional Redis-backed cache
class RedisQueryCache(QueryCache):
    def __init__(
        self,
        redis_client,
        ttl_seconds: int = 600,
        max_items: int = 500,
        namespace: str = "ctx:qcache",
    ):
        super().__init__(ttl_seconds=ttl_seconds, max_items=max_items)
        self.r = redis_client
        self.ns = namespace
        self.keys_list = f"{self.ns}:keys"

    def _rk(self, k: str) -> str:
        return f"{self.ns}:item:{k}"

    def get(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        import json

        k = self._key(query, filters)
        data = self.r.get(self._rk(k))
        if not data:
            return None
        try:
            return json.loads(data)
        except Exception:
            return None

    def set(
        self,
        query: str,
        value: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ):
        import json

        k = self._key(query, filters)
        rk = self._rk(k)
        pipe = self.r.pipeline()
        pipe.setex(rk, self.ttl, json.dumps(value))
        pipe.lpush(self.keys_list, rk)
        pipe.ltrim(self.keys_list, 0, self.max_items - 1)
        pipe.execute()


_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    global _query_cache
    if _query_cache is None:
        # Feature flag and optional dependency
        try:
            from src.config.settings import settings

            use_redis = bool(
                getattr(settings, "query_cache_redis_enabled", False)
            ) and bool(getattr(settings, "redis_url", None))
        except Exception:
            use_redis = False
        if use_redis:
            try:
                import redis  # type: ignore

                client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                _query_cache = RedisQueryCache(
                    client,
                    ttl_seconds=settings.cache_ttl_seconds,
                    max_items=settings.cache_max_items,
                )
                return _query_cache
            except Exception:
                # Fallback to in-memory
                _query_cache = QueryCache(
                    ttl_seconds=getattr(settings, "cache_ttl_seconds", 600),
                    max_items=getattr(settings, "cache_max_items", 500),
                )
                return _query_cache
        else:
            # In-memory default
            from src.config.settings import settings

            _query_cache = QueryCache(
                ttl_seconds=getattr(settings, "cache_ttl_seconds", 600),
                max_items=getattr(settings, "cache_max_items", 500),
            )
    return _query_cache


# Module-level stub function for MCP tool integration
def get_cached_result(query: str) -> Dict[str, Any]:
    """
    Get cached query result.

    Stub implementation for MCP tool integration.

    Args:
        query: Query string to look up

    Returns:
        Dict with status and cached result if found
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"QueryCache stub called with query: {query}")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "get_cached_result is a stub implementation",
        "results": [],
        "cache_hit": False,
        "data": {}
    }
