"""
Embedding Cache with Compression

Features:
- Pre-compute embeddings for common queries at startup
- Background refresh every 6 hours
- Warm cache with user's recent queries
- LZ4 compression for storage efficiency
- Integration with query patterns
"""

import asyncio
import hashlib
import json
import logging
import time
import threading
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Embedding cache with compression and background refresh

    Provides:
    - Pre-computed embeddings for common queries
    - LZ4 compression for storage efficiency
    - Background refresh every 6 hours
    - Warm cache from user's recent queries
    - Redis persistence
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_redis: bool = True,
        enable_compression: bool = True,
        ttl_seconds: int = 21600,  # 6 hours
        refresh_interval: int = 21600,  # 6 hours
        stats=None,
    ):
        """
        Initialize embedding cache

        Args:
            redis_url: Redis connection URL
            enable_redis: Whether to enable Redis storage
            enable_compression: Whether to enable LZ4 compression
            ttl_seconds: Cache TTL (default 6 hours)
            refresh_interval: Background refresh interval (default 6 hours)
            stats: CacheStats instance
        """
        self.ttl_seconds = ttl_seconds
        self.refresh_interval = refresh_interval
        self.enable_compression = enable_compression

        # Redis client
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
                    logger.info("Embedding cache with Redis initialized")
            except Exception as e:
                logger.warning(f"Redis embedding cache disabled: {e}")

        # Compression
        self.lz4_available = False
        if enable_compression:
            try:
                import lz4.frame  # type: ignore

                self.lz4 = lz4.frame
                self.lz4_available = True
                logger.info("LZ4 compression enabled for embeddings")
            except ImportError:
                logger.warning("LZ4 not available, compression disabled")

        # Stats
        from .stats import get_cache_stats

        self.stats = stats or get_cache_stats()

        # Common queries for pre-computation
        self.common_queries: Set[str] = set()

        # Background refresh task
        self.refresh_task = None
        self.running = False

        logger.info("Embedding cache initialized")

    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from settings"""
        try:
            from src.config.settings import settings

            return getattr(settings, "redis_url", None)
        except Exception:
            return None

    def _generate_key(self, text: str, model: str) -> str:
        """Generate cache key for embedding"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"emb:{model}:{text_hash}"

    def _compress(self, data: bytes) -> bytes:
        """Compress data using LZ4"""
        if self.lz4_available:
            return self.lz4.compress(data)
        return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data using LZ4"""
        if self.lz4_available:
            return self.lz4.decompress(data)
        return data

    async def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Get cached embedding

        Args:
            text: Text to get embedding for
            model: Model name

        Returns:
            Embedding vector or None
        """
        if not self.redis_enabled:
            return None

        start_time = time.time()
        key = self._generate_key(text, model)

        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                # Decompress and deserialize
                decompressed = self._decompress(cached_data)
                cached = json.loads(decompressed)

                # Update hit count
                cached["hit_count"] += 1
                cached["last_accessed"] = datetime.now(timezone.utc).isoformat()

                # Update cache with new hit count
                compressed = self._compress(json.dumps(cached).encode())
                self.redis_client.setex(key, self.ttl_seconds, compressed)

                latency = (time.time() - start_time) * 1000
                logger.debug(f"Embedding cache hit: {text[:50]}... ({latency:.2f}ms)")
                return cached["embedding"]

            return None

        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None

    async def set(self, text: str, embedding: List[float], model: str):
        """
        Cache embedding with compression

        Args:
            text: Text that was embedded
            embedding: Embedding vector
            model: Model name
        """
        if not self.redis_enabled:
            return

        try:
            key = self._generate_key(text, model)

            cached = {
                "text": text[:1000],  # Store truncated text
                "embedding": embedding,
                "model": model,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "last_accessed": datetime.now(timezone.utc).isoformat(),
                "hit_count": 0,
            }

            # Compress and store
            serialized = json.dumps(cached).encode()
            compressed = self._compress(serialized)

            self.redis_client.setex(key, self.ttl_seconds, compressed)

            # Calculate compression ratio
            compression_ratio = (
                len(serialized) / len(compressed) if self.lz4_available else 1.0
            )
            logger.debug(
                f"Cached embedding: {text[:50]}... "
                f"(compression: {compression_ratio:.2f}x)"
            )

        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

    async def precompute_common_queries(
        self, queries: List[str], model: str, embedding_func
    ):
        """
        Pre-compute embeddings for common queries

        Args:
            queries: List of common queries
            model: Model name
            embedding_func: Async function to generate embeddings
        """
        logger.info(f"Pre-computing embeddings for {len(queries)} common queries")

        self.common_queries.update(queries)
        computed = 0

        for query in queries:
            # Check if already cached
            cached = await self.get(query, model)
            if cached is not None:
                continue

            try:
                # Generate embedding
                embedding = await embedding_func(query)
                await self.set(query, embedding, model)
                computed += 1

                # Rate limiting (don't overwhelm embedding service)
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Failed to precompute embedding for '{query}': {e}")

        logger.info(f"Pre-computed {computed} new embeddings")

    async def warm_cache_from_recent_queries(
        self, user_id: str, model: str, embedding_func, limit: int = 50
    ):
        """
        Warm cache with user's recent queries

        Args:
            user_id: User ID
            model: Model name
            embedding_func: Async function to generate embeddings
            limit: Number of recent queries to cache
        """
        try:
            # Get recent queries from query history
            from src.search.query_history import get_query_history

            history = get_query_history()
            recent_queries = await history.get_recent_queries(user_id, limit=limit)

            logger.info(
                f"Warming cache with {len(recent_queries)} recent queries for user {user_id}"
            )

            for query_data in recent_queries:
                query = query_data.get("query", "")
                if not query:
                    continue

                # Check if already cached
                cached = await self.get(query, model)
                if cached is not None:
                    continue

                try:
                    # Generate and cache embedding
                    embedding = await embedding_func(query)
                    await self.set(query, embedding, model)
                    await asyncio.sleep(0.05)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Failed to warm cache for '{query}': {e}")

        except Exception as e:
            logger.warning(f"Failed to warm cache from recent queries: {e}")

    async def refresh_stale_embeddings(self, model: str, embedding_func):
        """
        Background task to refresh stale embeddings

        Args:
            model: Model name
            embedding_func: Async function to generate embeddings
        """
        logger.info("Starting background embedding refresh")

        if not self.redis_enabled:
            logger.warning("Redis disabled, skipping refresh")
            return

        try:
            # Scan for embeddings that need refresh
            pattern = f"emb:{model}:*"
            refreshed = 0

            for key in self.redis_client.scan_iter(match=pattern, count=100):
                try:
                    cached_data = self.redis_client.get(key)
                    if not cached_data:
                        continue

                    decompressed = self._decompress(cached_data)
                    cached = json.loads(decompressed)

                    # Check if needs refresh (based on hit count and age)
                    cached_at = datetime.fromisoformat(cached["cached_at"])
                    age_hours = (
                        datetime.now(timezone.utc) - cached_at
                    ).total_seconds() / 3600

                    # Refresh if high hit count or approaching TTL
                    if cached["hit_count"] > 10 or age_hours > (
                        self.ttl_seconds / 3600 * 0.8
                    ):
                        text = cached["text"]
                        embedding = await embedding_func(text)
                        await self.set(text, embedding, model)
                        refreshed += 1

                        await asyncio.sleep(0.1)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Failed to refresh embedding: {e}")

            logger.info(f"Refreshed {refreshed} embeddings")

        except Exception as e:
            logger.error(f"Background refresh failed: {e}")

    async def start_background_refresh(self, model: str, embedding_func):
        """
        Start background refresh task

        Args:
            model: Model name
            embedding_func: Async function to generate embeddings
        """
        if self.running:
            logger.warning("Background refresh already running")
            return

        self.running = True

        async def refresh_loop():
            while self.running:
                try:
                    await self.refresh_stale_embeddings(model, embedding_func)
                except Exception as e:
                    logger.error(f"Refresh loop error: {e}")

                # Wait for next refresh
                await asyncio.sleep(self.refresh_interval)

        self.refresh_task = asyncio.create_task(refresh_loop())
        logger.info(
            f"Background refresh started (interval: {self.refresh_interval}s)"
        )

    def stop_background_refresh(self):
        """Stop background refresh task"""
        self.running = False
        if self.refresh_task:
            self.refresh_task.cancel()
        logger.info("Background refresh stopped")

    async def invalidate_model(self, model: str):
        """
        Invalidate all cached embeddings for a model

        Args:
            model: Model name
        """
        if not self.redis_enabled:
            return

        try:
            pattern = f"emb:{model}:*"
            count = 0

            for key in self.redis_client.scan_iter(match=pattern, count=100):
                self.redis_client.delete(key)
                count += 1

            logger.info(f"Invalidated {count} embeddings for model: {model}")

        except Exception as e:
            logger.error(f"Failed to invalidate model embeddings: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "redis_enabled": self.redis_enabled,
            "compression_enabled": self.lz4_available,
            "ttl_seconds": self.ttl_seconds,
            "refresh_interval": self.refresh_interval,
            "common_queries_count": len(self.common_queries),
            "background_refresh_running": self.running,
        }

        # Get cache size from Redis
        if self.redis_enabled:
            try:
                pattern = "emb:*"
                count = sum(1 for _ in self.redis_client.scan_iter(match=pattern))
                stats["cached_embeddings_count"] = count
            except Exception as e:
                logger.warning(f"Failed to get cache size: {e}")

        return stats


# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None
_cache_lock = threading.Lock()


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance"""
    global _embedding_cache
    if _embedding_cache is None:
        with _cache_lock:
            if _embedding_cache is None:
                _embedding_cache = EmbeddingCache()
    return _embedding_cache
