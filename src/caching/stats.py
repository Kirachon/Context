"""
Cache Statistics & Monitoring

Tracks cache performance metrics and exposes them to Prometheus:
- Hit rates (L1, L2, L3, miss)
- Cache sizes
- Invalidation events
- Latency metrics
"""

import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache metrics for a specific layer"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    invalidations: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    size_bytes: int = 0
    item_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency"""
        total_ops = self.hits + self.misses + self.sets
        return self.total_latency_ms / total_ops if total_ops > 0 else 0.0


@dataclass
class CacheStats:
    """
    Multi-layer cache statistics with Prometheus metrics support

    Tracks performance across L1 (in-memory), L2 (Redis), and L3 (pre-computed)
    cache layers, plus overall statistics.
    """

    l1_metrics: CacheMetrics = field(default_factory=CacheMetrics)
    l2_metrics: CacheMetrics = field(default_factory=CacheMetrics)
    l3_metrics: CacheMetrics = field(default_factory=CacheMetrics)

    # Overall stats
    total_requests: int = 0
    prefetch_count: int = 0
    prefetch_hits: int = 0
    file_invalidations: int = 0

    # Pattern analysis
    query_patterns: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_hit(self, layer: str, latency_ms: float = 0.0):
        """Record cache hit"""
        with self._lock:
            self.total_requests += 1
            if layer == "l1":
                self.l1_metrics.hits += 1
                self.l1_metrics.total_latency_ms += latency_ms
            elif layer == "l2":
                self.l2_metrics.hits += 1
                self.l2_metrics.total_latency_ms += latency_ms
            elif layer == "l3":
                self.l3_metrics.hits += 1
                self.l3_metrics.total_latency_ms += latency_ms

    def record_miss(self, latency_ms: float = 0.0):
        """Record cache miss (all layers)"""
        with self._lock:
            self.total_requests += 1
            self.l1_metrics.misses += 1
            self.l2_metrics.misses += 1
            self.l3_metrics.misses += 1
            self.l1_metrics.total_latency_ms += latency_ms

    def record_set(self, layer: str, size_bytes: int = 0):
        """Record cache set operation"""
        with self._lock:
            if layer == "l1":
                self.l1_metrics.sets += 1
                self.l1_metrics.item_count += 1
                self.l1_metrics.size_bytes += size_bytes
            elif layer == "l2":
                self.l2_metrics.sets += 1
                self.l2_metrics.item_count += 1
                self.l2_metrics.size_bytes += size_bytes
            elif layer == "l3":
                self.l3_metrics.sets += 1
                self.l3_metrics.item_count += 1
                self.l3_metrics.size_bytes += size_bytes

    def record_eviction(self, layer: str, size_bytes: int = 0):
        """Record cache eviction"""
        with self._lock:
            if layer == "l1":
                self.l1_metrics.evictions += 1
                self.l1_metrics.item_count = max(0, self.l1_metrics.item_count - 1)
                self.l1_metrics.size_bytes = max(
                    0, self.l1_metrics.size_bytes - size_bytes
                )
            elif layer == "l2":
                self.l2_metrics.evictions += 1
                self.l2_metrics.item_count = max(0, self.l2_metrics.item_count - 1)
                self.l2_metrics.size_bytes = max(
                    0, self.l2_metrics.size_bytes - size_bytes
                )

    def record_invalidation(self, layer: str, count: int = 1):
        """Record cache invalidation"""
        with self._lock:
            if layer == "l1":
                self.l1_metrics.invalidations += count
            elif layer == "l2":
                self.l2_metrics.invalidations += count
            elif layer == "file":
                self.file_invalidations += count

    def record_error(self, layer: str):
        """Record cache error"""
        with self._lock:
            if layer == "l1":
                self.l1_metrics.errors += 1
            elif layer == "l2":
                self.l2_metrics.errors += 1
            elif layer == "l3":
                self.l3_metrics.errors += 1

    def record_prefetch(self, hit: bool = False):
        """Record prefetch operation"""
        with self._lock:
            self.prefetch_count += 1
            if hit:
                self.prefetch_hits += 1

    def record_query_pattern(self, pattern: str):
        """Record query pattern for analysis"""
        with self._lock:
            self.query_patterns[pattern] += 1

    def get_overall_hit_rate(self) -> float:
        """Calculate overall cache hit rate"""
        total_hits = (
            self.l1_metrics.hits + self.l2_metrics.hits + self.l3_metrics.hits
        )
        return (
            (total_hits / self.total_requests * 100) if self.total_requests > 0 else 0.0
        )

    def get_prefetch_effectiveness(self) -> float:
        """Calculate prefetch effectiveness"""
        return (
            (self.prefetch_hits / self.prefetch_count * 100)
            if self.prefetch_count > 0
            else 0.0
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get complete statistics summary"""
        return {
            "overall": {
                "total_requests": self.total_requests,
                "hit_rate_percent": round(self.get_overall_hit_rate(), 2),
                "prefetch_count": self.prefetch_count,
                "prefetch_effectiveness_percent": round(
                    self.get_prefetch_effectiveness(), 2
                ),
                "file_invalidations": self.file_invalidations,
            },
            "l1": {
                "hits": self.l1_metrics.hits,
                "misses": self.l1_metrics.misses,
                "hit_rate_percent": round(self.l1_metrics.hit_rate, 2),
                "sets": self.l1_metrics.sets,
                "evictions": self.l1_metrics.evictions,
                "invalidations": self.l1_metrics.invalidations,
                "errors": self.l1_metrics.errors,
                "avg_latency_ms": round(self.l1_metrics.avg_latency_ms, 2),
                "size_bytes": self.l1_metrics.size_bytes,
                "item_count": self.l1_metrics.item_count,
            },
            "l2": {
                "hits": self.l2_metrics.hits,
                "misses": self.l2_metrics.misses,
                "hit_rate_percent": round(self.l2_metrics.hit_rate, 2),
                "sets": self.l2_metrics.sets,
                "evictions": self.l2_metrics.evictions,
                "invalidations": self.l2_metrics.invalidations,
                "errors": self.l2_metrics.errors,
                "avg_latency_ms": round(self.l2_metrics.avg_latency_ms, 2),
                "size_bytes": self.l2_metrics.size_bytes,
                "item_count": self.l2_metrics.item_count,
            },
            "l3": {
                "hits": self.l3_metrics.hits,
                "misses": self.l3_metrics.misses,
                "hit_rate_percent": round(self.l3_metrics.hit_rate, 2),
                "sets": self.l3_metrics.sets,
                "invalidations": self.l3_metrics.invalidations,
                "errors": self.l3_metrics.errors,
                "item_count": self.l3_metrics.item_count,
            },
            "top_patterns": sorted(
                self.query_patterns.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format

        Returns:
            Prometheus-formatted metrics string
        """
        metrics = []

        # Cache hits by layer
        metrics.append("# HELP cache_hits_total Total cache hits by layer")
        metrics.append("# TYPE cache_hits_total counter")
        metrics.append(f'cache_hits_total{{layer="l1"}} {self.l1_metrics.hits}')
        metrics.append(f'cache_hits_total{{layer="l2"}} {self.l2_metrics.hits}')
        metrics.append(f'cache_hits_total{{layer="l3"}} {self.l3_metrics.hits}')

        # Cache misses
        metrics.append("# HELP cache_misses_total Total cache misses")
        metrics.append("# TYPE cache_misses_total counter")
        metrics.append(
            f"cache_misses_total {self.l1_metrics.misses}"
        )  # Misses recorded at L1

        # Hit rate by layer
        metrics.append("# HELP cache_hit_rate_percent Cache hit rate by layer")
        metrics.append("# TYPE cache_hit_rate_percent gauge")
        metrics.append(
            f'cache_hit_rate_percent{{layer="l1"}} {self.l1_metrics.hit_rate:.2f}'
        )
        metrics.append(
            f'cache_hit_rate_percent{{layer="l2"}} {self.l2_metrics.hit_rate:.2f}'
        )
        metrics.append(
            f'cache_hit_rate_percent{{layer="l3"}} {self.l3_metrics.hit_rate:.2f}'
        )
        metrics.append(
            f'cache_hit_rate_percent{{layer="overall"}} {self.get_overall_hit_rate():.2f}'
        )

        # Cache size
        metrics.append("# HELP cache_size_bytes Cache size in bytes by layer")
        metrics.append("# TYPE cache_size_bytes gauge")
        metrics.append(f'cache_size_bytes{{layer="l1"}} {self.l1_metrics.size_bytes}')
        metrics.append(f'cache_size_bytes{{layer="l2"}} {self.l2_metrics.size_bytes}')

        # Item count
        metrics.append("# HELP cache_items_count Number of cached items by layer")
        metrics.append("# TYPE cache_items_count gauge")
        metrics.append(f'cache_items_count{{layer="l1"}} {self.l1_metrics.item_count}')
        metrics.append(f'cache_items_count{{layer="l2"}} {self.l2_metrics.item_count}')
        metrics.append(f'cache_items_count{{layer="l3"}} {self.l3_metrics.item_count}')

        # Evictions
        metrics.append("# HELP cache_evictions_total Total cache evictions")
        metrics.append("# TYPE cache_evictions_total counter")
        metrics.append(
            f'cache_evictions_total{{layer="l1"}} {self.l1_metrics.evictions}'
        )
        metrics.append(
            f'cache_evictions_total{{layer="l2"}} {self.l2_metrics.evictions}'
        )

        # Invalidations
        metrics.append("# HELP cache_invalidations_total Total cache invalidations")
        metrics.append("# TYPE cache_invalidations_total counter")
        metrics.append(
            f'cache_invalidations_total{{layer="l1"}} {self.l1_metrics.invalidations}'
        )
        metrics.append(
            f'cache_invalidations_total{{layer="l2"}} {self.l2_metrics.invalidations}'
        )
        metrics.append(
            f'cache_invalidations_total{{layer="file"}} {self.file_invalidations}'
        )

        # Latency
        metrics.append("# HELP cache_avg_latency_ms Average cache operation latency")
        metrics.append("# TYPE cache_avg_latency_ms gauge")
        metrics.append(
            f'cache_avg_latency_ms{{layer="l1"}} {self.l1_metrics.avg_latency_ms:.2f}'
        )
        metrics.append(
            f'cache_avg_latency_ms{{layer="l2"}} {self.l2_metrics.avg_latency_ms:.2f}'
        )

        # Prefetch metrics
        metrics.append("# HELP cache_prefetch_total Total prefetch operations")
        metrics.append("# TYPE cache_prefetch_total counter")
        metrics.append(f"cache_prefetch_total {self.prefetch_count}")

        metrics.append(
            "# HELP cache_prefetch_effectiveness_percent Prefetch effectiveness"
        )
        metrics.append("# TYPE cache_prefetch_effectiveness_percent gauge")
        metrics.append(
            f"cache_prefetch_effectiveness_percent {self.get_prefetch_effectiveness():.2f}"
        )

        # Errors
        metrics.append("# HELP cache_errors_total Total cache errors")
        metrics.append("# TYPE cache_errors_total counter")
        metrics.append(f'cache_errors_total{{layer="l1"}} {self.l1_metrics.errors}')
        metrics.append(f'cache_errors_total{{layer="l2"}} {self.l2_metrics.errors}')
        metrics.append(f'cache_errors_total{{layer="l3"}} {self.l3_metrics.errors}')

        return "\n".join(metrics)

    def reset(self):
        """Reset all statistics"""
        with self._lock:
            self.l1_metrics = CacheMetrics()
            self.l2_metrics = CacheMetrics()
            self.l3_metrics = CacheMetrics()
            self.total_requests = 0
            self.prefetch_count = 0
            self.prefetch_hits = 0
            self.file_invalidations = 0
            self.query_patterns.clear()


# Global stats instance
_cache_stats: Optional[CacheStats] = None
_stats_lock = threading.Lock()


def get_cache_stats() -> CacheStats:
    """Get global cache statistics instance"""
    global _cache_stats
    if _cache_stats is None:
        with _stats_lock:
            if _cache_stats is None:
                _cache_stats = CacheStats()
    return _cache_stats
