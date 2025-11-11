"""
Multi-Layer Query Cache

Implements a 3-tier caching strategy:
- L1: In-memory Python dict with LRU eviction (100MB, 5min TTL)
- L2: Redis cache (1GB, 1hour TTL)
- L3: Pre-computed common queries (24hour TTL)

Features:
- Automatic cache key generation from query + context
- Cache invalidation on file changes
- LRU eviction policy
- Promotion from L2 -> L1 on hit
"""

import asyncio
import hashlib
import json
import logging
import pickle
import sys
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set
import threading

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe LRU cache with size and TTL limits

    Uses OrderedDict for O(1) access and LRU eviction
    """

    def __init__(self, max_size_bytes: int = 100_000_000, ttl_seconds: int = 300):
        """
        Args:
            max_size_bytes: Maximum cache size (default 100MB)
            ttl_seconds: Time-to-live for entries (default 5min)
        """
        self.max_size_bytes = max_size_bytes
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._current_size = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, moving to end (most recently used)"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check TTL
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                self._remove_entry(key)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry["value"]

    def set(self, key: str, value: Any) -> int:
        """
        Set value in cache with LRU eviction

        Returns:
            Size in bytes of the cached value
        """
        with self._lock:
            # Calculate size
            size = sys.getsizeof(pickle.dumps(value))

            # Evict if needed
            while (
                self._current_size + size > self.max_size_bytes and len(self._cache) > 0
            ):
                self._evict_lru()

            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)

            # Add new entry
            self._cache[key] = {"value": value, "timestamp": time.time(), "size": size}
            self._current_size += size

            return size

    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self):
        """Clear all entries"""
        with self._lock:
            self._cache.clear()
            self._current_size = 0

    def size_bytes(self) -> int:
        """Get current cache size in bytes"""
        with self._lock:
            return self._current_size

    def item_count(self) -> int:
        """Get number of items in cache"""
        with self._lock:
            return len(self._cache)

    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._cache:
            return

        key, _ = self._cache.popitem(last=False)  # Remove first (LRU)
        logger.debug(f"Evicted LRU entry: {key[:16]}...")

    def _remove_entry(self, key: str):
        """Remove entry and update size"""
        entry = self._cache.pop(key)
        self._current_size -= entry["size"]


class QueryCache:
    """
    Multi-layer query result cache with Redis backend

    Provides:
    - L1: In-memory LRU cache (100MB, 5min TTL) for hot queries
    - L2: Redis cache (1GB, 1hour TTL) for warm queries
    - L3: Pre-computed cache (24hour TTL) for common queries
    - Smart invalidation on file changes
    - Cache key generation from query + context
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_redis: bool = True,
        stats=None,
    ):
        """
        Initialize multi-layer cache

        Args:
            redis_url: Redis connection URL
            enable_redis: Whether to enable Redis (L2) layer
            stats: CacheStats instance for metrics
        """
        # L1: In-memory cache
        self.l1 = LRUCache(max_size_bytes=100_000_000, ttl_seconds=300)  # 100MB, 5min

        # L2: Redis cache
        self.redis_client = None
        self.redis_enabled = False
        if enable_redis:
            try:
                import redis

                url = redis_url or self._get_redis_url()
                if url:
                    self.redis_client = redis.from_url(
                        url, decode_responses=False, socket_connect_timeout=5
                    )
                    self.redis_client.ping()
                    self.redis_enabled = True
                    logger.info("Redis cache (L2) initialized")
            except Exception as e:
                logger.warning(f"Redis cache disabled: {e}")

        # L3: Pre-computed queries
        self.l3_queries: Set[str] = set()

        # Stats
        from .stats import get_cache_stats

        self.stats = stats or get_cache_stats()

        # File -> Query mapping for invalidation
        self._file_query_map: Dict[str, Set[str]] = {}
        self._query_file_map: Dict[str, Set[str]] = {}
        self._map_lock = threading.Lock()

        logger.info("Multi-layer query cache initialized")

    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from settings"""
        try:
            from src.config.settings import settings

            return getattr(settings, "redis_url", None)
        except Exception:
            return None

    def generate_cache_key(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate deterministic cache key from query and context

        Args:
            query: Search query string
            context: Search context (current file, recent files, etc.)

        Returns:
            SHA256 hash of query + context
        """
        key_parts = [query]

        if context:
            # Add context components that affect search results
            if "current_project" in context:
                key_parts.append(f"project:{context['current_project']}")

            if "recent_files" in context:
                # Use top 5 recent files
                recent = context["recent_files"][:5] if context["recent_files"] else []
                key_parts.append(f"recent:{','.join(sorted(recent))}")

            if "filters" in context:
                # Include filters in cache key
                key_parts.append(f"filters:{json.dumps(context['filters'], sort_keys=True)}")

        # Generate SHA256 hash
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def get(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Any]]:
        """
        Get cached query results (L1 -> L2 -> L3 -> Miss)

        Args:
            query: Search query
            context: Search context

        Returns:
            Cached results or None if not found
        """
        start_time = time.time()
        query_key = self.generate_cache_key(query, context)

        # L1: In-memory cache
        result = self.l1.get(query_key)
        if result is not None:
            latency = (time.time() - start_time) * 1000
            self.stats.record_hit("l1", latency)
            logger.debug(f"L1 cache hit: {query[:50]}... ({latency:.2f}ms)")
            return result

        # L2: Redis cache
        if self.redis_enabled:
            try:
                cached_data = self.redis_client.get(f"qcache:{query_key}")
                if cached_data:
                    result = pickle.loads(cached_data)
                    latency = (time.time() - start_time) * 1000
                    self.stats.record_hit("l2", latency)
                    logger.debug(f"L2 cache hit: {query[:50]}... ({latency:.2f}ms)")

                    # Promote to L1
                    size = self.l1.set(query_key, result)
                    self.stats.record_set("l1", size)

                    return result
            except Exception as e:
                logger.warning(f"L2 cache error: {e}")
                self.stats.record_error("l2")

        # L3: Pre-computed queries
        if query_key in self.l3_queries:
            try:
                if self.redis_enabled:
                    cached_data = self.redis_client.get(f"qcache:l3:{query_key}")
                    if cached_data:
                        result = pickle.loads(cached_data)
                        latency = (time.time() - start_time) * 1000
                        self.stats.record_hit("l3", latency)
                        logger.debug(
                            f"L3 cache hit: {query[:50]}... ({latency:.2f}ms)"
                        )

                        # Promote to L1 and L2
                        size = self.l1.set(query_key, result)
                        self.stats.record_set("l1", size)
                        if self.redis_enabled:
                            self._set_redis(f"qcache:{query_key}", result, ttl=3600)

                        return result
            except Exception as e:
                logger.warning(f"L3 cache error: {e}")
                self.stats.record_error("l3")

        # Cache miss
        latency = (time.time() - start_time) * 1000
        self.stats.record_miss(latency)
        logger.debug(f"Cache miss: {query[:50]}... ({latency:.2f}ms)")
        return None

    async def set(
        self,
        query: str,
        results: List[Any],
        context: Optional[Dict[str, Any]] = None,
        accessed_files: Optional[List[str]] = None,
        ttl: int = 3600,
    ):
        """
        Cache query results in L1 and L2

        Args:
            query: Search query
            results: Search results to cache
            context: Search context
            accessed_files: Files accessed during search (for invalidation)
            ttl: Time-to-live in seconds (for L2)
        """
        query_key = self.generate_cache_key(query, context)

        # Store in L1
        size = self.l1.set(query_key, results)
        self.stats.record_set("l1", size)

        # Store in L2 (Redis)
        if self.redis_enabled:
            try:
                self._set_redis(f"qcache:{query_key}", results, ttl)
                self.stats.record_set("l2", len(pickle.dumps(results)))
            except Exception as e:
                logger.warning(f"Failed to cache in L2: {e}")
                self.stats.record_error("l2")

        # Track file-query relationships for invalidation
        if accessed_files:
            self._track_file_access(query_key, accessed_files)

        logger.debug(f"Cached query: {query[:50]}... ({len(results)} results)")

    def _set_redis(self, key: str, value: Any, ttl: int):
        """Set value in Redis with TTL"""
        if self.redis_enabled:
            self.redis_client.setex(key, ttl, pickle.dumps(value))

    async def invalidate_file(self, file_path: str):
        """
        Invalidate all queries that accessed a specific file

        Args:
            file_path: Path to the file that changed
        """
        with self._map_lock:
            affected_queries = self._file_query_map.get(file_path, set()).copy()

        if not affected_queries:
            return

        logger.info(
            f"Invalidating {len(affected_queries)} queries for file: {file_path}"
        )

        # Invalidate in L1 and L2
        for query_key in affected_queries:
            # L1
            if self.l1.delete(query_key):
                self.stats.record_invalidation("l1")

            # L2
            if self.redis_enabled:
                try:
                    self.redis_client.delete(f"qcache:{query_key}")
                    self.stats.record_invalidation("l2")
                except Exception as e:
                    logger.warning(f"Failed to invalidate L2: {e}")

        # Update tracking
        with self._map_lock:
            for query_key in affected_queries:
                if query_key in self._query_file_map:
                    self._query_file_map[query_key].discard(file_path)

            if file_path in self._file_query_map:
                del self._file_query_map[file_path]

        self.stats.record_invalidation("file", len(affected_queries))

    async def invalidate_batch(self, file_paths: List[str]):
        """
        Batch invalidate multiple files

        Args:
            file_paths: List of file paths that changed
        """
        logger.info(f"Batch invalidating {len(file_paths)} files")

        tasks = [self.invalidate_file(fp) for fp in file_paths]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _track_file_access(self, query_key: str, file_paths: List[str]):
        """Track which files were accessed by a query"""
        with self._map_lock:
            # Query -> Files
            if query_key not in self._query_file_map:
                self._query_file_map[query_key] = set()
            self._query_file_map[query_key].update(file_paths)

            # File -> Queries
            for file_path in file_paths:
                if file_path not in self._file_query_map:
                    self._file_query_map[file_path] = set()
                self._file_query_map[file_path].add(query_key)

    async def precompute_query(self, query: str, results: List[Any], ttl: int = 86400):
        """
        Store query in L3 pre-computed cache

        Args:
            query: Common query to precompute
            results: Query results
            ttl: TTL in seconds (default 24 hours)
        """
        query_key = self.generate_cache_key(query)
        self.l3_queries.add(query_key)

        if self.redis_enabled:
            try:
                self._set_redis(f"qcache:l3:{query_key}", results, ttl)
                self.stats.record_set("l3", len(pickle.dumps(results)))
                logger.info(f"Pre-computed query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to precompute query: {e}")
                self.stats.record_error("l3")

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "l1": {
                "size_bytes": self.l1.size_bytes(),
                "item_count": self.l1.item_count(),
                "max_size_bytes": self.l1.max_size_bytes,
                "ttl_seconds": self.l1.ttl_seconds,
            },
            "l2": {"enabled": self.redis_enabled},
            "l3": {"precomputed_queries": len(self.l3_queries)},
            "tracking": {
                "tracked_files": len(self._file_query_map),
                "tracked_queries": len(self._query_file_map),
            },
        }

    def clear_all(self):
        """Clear all cache layers"""
        self.l1.clear()

        if self.redis_enabled:
            try:
                # Delete all qcache:* keys
                for key in self.redis_client.scan_iter(match="qcache:*"):
                    self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Failed to clear L2: {e}")

        self.l3_queries.clear()
        self._file_query_map.clear()
        self._query_file_map.clear()

        logger.info("All cache layers cleared")


# Global cache instance
_query_cache: Optional[QueryCache] = None
_cache_lock = threading.Lock()


def get_query_cache() -> QueryCache:
    """Get global query cache instance"""
    global _query_cache
    if _query_cache is None:
        with _cache_lock:
            if _query_cache is None:
                _query_cache = QueryCache()
    return _query_cache
