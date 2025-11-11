"""
Smart Caching System for Context Workspace v2.5

This module provides a multi-layer caching system that achieves sub-100ms
search latency through aggressive caching and predictive pre-fetching.

Components:
- QueryCache: Multi-layer query result cache (L1, L2, L3)
- EmbeddingCache: Embedding caching with compression
- CacheInvalidator: Smart invalidation based on file changes
- PredictivePrefetcher: Pattern-based query prediction
- CacheStats: Prometheus metrics and monitoring
"""

from .query_cache import QueryCache, get_query_cache
from .embedding_cache import EmbeddingCache, get_embedding_cache
from .invalidation import CacheInvalidator, get_cache_invalidator
from .prefetcher import PredictivePrefetcher, get_prefetcher
from .stats import CacheStats, get_cache_stats

__all__ = [
    "QueryCache",
    "get_query_cache",
    "EmbeddingCache",
    "get_embedding_cache",
    "CacheInvalidator",
    "get_cache_invalidator",
    "PredictivePrefetcher",
    "get_prefetcher",
    "CacheStats",
    "get_cache_stats",
]
