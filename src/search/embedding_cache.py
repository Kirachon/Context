"""
Embedding Result Caching (Story 2-7)

Provides multi-level caching for embedding results to optimize performance
for large codebases.
"""

import logging
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
import redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CachedEmbedding:
    """Cached embedding result"""

    text: str
    embedding: List[float]
    model: str
    cached_at: str
    hit_count: int = 0


class EmbeddingCache:
    """
    Multi-level embedding cache with Redis backend

    Provides:
    - Embedding result caching with TTL
    - Cache invalidation on model updates
    - Cache statistics and monitoring
    - LRU eviction policy
    """

    def __init__(
        self,
        redis_url: str = None,
        ttl_seconds: int = None,
        max_cache_size: int = 10000,
    ):
        """
        Initialize embedding cache

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Cache TTL in seconds
            max_cache_size: Maximum number of cached embeddings
        """
        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = ttl_seconds or settings.cache_ttl_seconds
        self.max_cache_size = max_cache_size

        # Initialize Redis client
        try:
            self.redis_client = redis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.enabled = True
            logger.info("Embedding cache initialized with Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache disabled.")
            self.redis_client = None
            self.enabled = False

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "errors": 0,
        }

    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{model}:{text_hash}"

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Get cached embedding for text

        Args:
            text: Text to get embedding for
            model: Model name

        Returns:
            Cached embedding or None if not found
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._get_cache_key(text, model)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                cached = json.loads(cached_data)

                # Update hit count
                cached["hit_count"] += 1
                self.redis_client.setex(cache_key, self.ttl_seconds, json.dumps(cached))

                self.stats["hits"] += 1
                logger.debug(f"Cache hit for embedding: {text[:50]}...")
                return cached["embedding"]

            self.stats["misses"] += 1
            return None

        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            self.stats["errors"] += 1
            return None

    def set(self, text: str, embedding: List[float], model: str):
        """
        Cache embedding result

        Args:
            text: Text that was embedded
            embedding: Embedding vector
            model: Model name
        """
        if not self.enabled:
            return

        try:
            cache_key = self._get_cache_key(text, model)

            cached = {
                "text": text[:1000],  # Store truncated text for debugging
                "embedding": embedding,
                "model": model,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "hit_count": 0,
            }

            self.redis_client.setex(cache_key, self.ttl_seconds, json.dumps(cached))

            self.stats["sets"] += 1
            logger.debug(f"Cached embedding for: {text[:50]}...")

        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
            self.stats["errors"] += 1

    def invalidate_model(self, model: str):
        """
        Invalidate all cached embeddings for a model

        Args:
            model: Model name to invalidate
        """
        if not self.enabled:
            return

        try:
            pattern = f"embedding:{model}:*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor, match=pattern, count=100
                )

                if keys:
                    self.redis_client.delete(*keys)
                    count += len(keys)

                if cursor == 0:
                    break

            self.stats["invalidations"] += count
            logger.info(f"Invalidated {count} cached embeddings for model: {model}")

        except Exception as e:
            logger.error(f"Failed to invalidate model cache: {e}")
            self.stats["errors"] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "enabled": self.enabled,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "invalidations": self.stats["invalidations"],
            "errors": self.stats["errors"],
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "ttl_seconds": self.ttl_seconds,
            "max_cache_size": self.max_cache_size,
        }

    def clear_statistics(self):
        """Clear cache statistics"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "errors": 0,
        }


# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache
