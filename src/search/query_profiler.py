"""
Query Performance Profiler (Story 2-7, Phase 3)

Profiles and analyzes query performance for optimization.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryProfile:
    """Profile for a single query execution"""

    query: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0

    # Phase timings
    parsing_time: float = 0.0
    vector_search_time: float = 0.0
    ranking_time: float = 0.0
    filtering_time: float = 0.0

    # Results
    results_count: int = 0
    cache_hit: bool = False

    def complete(self):
        """Mark profile as complete"""
        self.end_time = datetime.now(timezone.utc)
        self.total_duration = (self.end_time - self.start_time).total_seconds()


class QueryProfiler:
    """
    Profiles query execution for performance analysis

    Tracks:
    - Query execution time
    - Phase-specific timings
    - Cache hit rates
    - Performance trends
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize query profiler

        Args:
            max_history: Maximum profiles to keep
        """
        self.max_history = max_history
        self.profiles: List[QueryProfile] = []
        self.current_profile: Optional[QueryProfile] = None

        # Statistics
        self.stats = {
            "total_queries": 0,
            "avg_duration": 0.0,
            "cache_hit_rate": 0.0,
            "slow_queries": 0,
            "slow_query_threshold": 1.0,  # seconds
        }

        # Phase statistics
        self.phase_stats = defaultdict(
            lambda: {"total_time": 0.0, "count": 0, "avg_time": 0.0}
        )

    def start_query(self, query: str) -> QueryProfile:
        """
        Start profiling a query

        Args:
            query: Query string

        Returns:
            QueryProfile instance
        """
        profile = QueryProfile(query=query, start_time=datetime.now(timezone.utc))
        self.current_profile = profile
        return profile

    def end_query(self, results_count: int = 0, cache_hit: bool = False):
        """
        End query profiling

        Args:
            results_count: Number of results returned
            cache_hit: Whether result was from cache
        """
        if not self.current_profile:
            logger.warning("No active query profile")
            return

        profile = self.current_profile
        profile.results_count = results_count
        profile.cache_hit = cache_hit
        profile.complete()

        # Store profile
        self.profiles.append(profile)
        if len(self.profiles) > self.max_history:
            self.profiles.pop(0)

        # Update statistics
        self._update_statistics()

        logger.debug(
            f"Query profiled: {profile.query[:50]}... "
            f"({profile.total_duration:.3f}s, "
            f"cache_hit={cache_hit})"
        )

        self.current_profile = None

    def record_phase(self, phase_name: str, duration: float):
        """
        Record time for a query phase

        Args:
            phase_name: Name of phase (e.g., 'parsing', 'vector_search')
            duration: Duration in seconds
        """
        if not self.current_profile:
            logger.warning("No active query profile")
            return

        # Update profile
        if phase_name == "parsing":
            self.current_profile.parsing_time += duration
        elif phase_name == "vector_search":
            self.current_profile.vector_search_time += duration
        elif phase_name == "ranking":
            self.current_profile.ranking_time += duration
        elif phase_name == "filtering":
            self.current_profile.filtering_time += duration

        # Update phase statistics
        self.phase_stats[phase_name]["total_time"] += duration
        self.phase_stats[phase_name]["count"] += 1
        self.phase_stats[phase_name]["avg_time"] = (
            self.phase_stats[phase_name]["total_time"]
            / self.phase_stats[phase_name]["count"]
        )

    def _update_statistics(self):
        """Update aggregate statistics"""
        if not self.profiles:
            return

        self.stats["total_queries"] = len(self.profiles)

        # Average duration
        total_duration = sum(p.total_duration for p in self.profiles)
        self.stats["avg_duration"] = total_duration / len(self.profiles)

        # Cache hit rate
        cache_hits = sum(1 for p in self.profiles if p.cache_hit)
        self.stats["cache_hit_rate"] = cache_hits / len(self.profiles) * 100

        # Slow queries
        slow_threshold = self.stats["slow_query_threshold"]
        self.stats["slow_queries"] = sum(
            1 for p in self.profiles if p.total_duration > slow_threshold
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get profiling statistics"""
        return {
            "total_queries": self.stats["total_queries"],
            "avg_duration": round(self.stats["avg_duration"], 3),
            "cache_hit_rate": round(self.stats["cache_hit_rate"], 2),
            "slow_queries": self.stats["slow_queries"],
            "slow_query_threshold": self.stats["slow_query_threshold"],
            "phase_stats": {
                phase: {
                    "avg_time": round(stats["avg_time"], 3),
                    "total_time": round(stats["total_time"], 3),
                    "count": stats["count"],
                }
                for phase, stats in self.phase_stats.items()
            },
        }

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get slowest queries

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of slow query profiles
        """
        sorted_profiles = sorted(
            self.profiles, key=lambda p: p.total_duration, reverse=True
        )

        return [
            {
                "query": p.query,
                "duration": round(p.total_duration, 3),
                "results_count": p.results_count,
                "cache_hit": p.cache_hit,
                "parsing_time": round(p.parsing_time, 3),
                "vector_search_time": round(p.vector_search_time, 3),
                "ranking_time": round(p.ranking_time, 3),
                "filtering_time": round(p.filtering_time, 3),
            }
            for p in sorted_profiles[:limit]
        ]

    def get_optimization_recommendations(self) -> List[str]:
        """
        Get optimization recommendations based on profiles

        Returns:
            List of recommendations
        """
        recommendations = []

        if not self.profiles:
            return recommendations

        stats = self.get_statistics()

        # Check cache hit rate
        if stats["cache_hit_rate"] < 30:
            recommendations.append(
                "Low cache hit rate. Consider increasing cache size or TTL."
            )

        # Check slow queries
        if stats["slow_queries"] > len(self.profiles) * 0.1:
            recommendations.append(
                "High number of slow queries. Consider query optimization."
            )

        # Check phase times
        phase_stats = stats["phase_stats"]
        if "vector_search" in phase_stats:
            vs_time = phase_stats["vector_search"]["avg_time"]
            if vs_time > 0.5:
                recommendations.append(
                    "Vector search is slow. Consider index optimization."
                )

        if "ranking" in phase_stats:
            rank_time = phase_stats["ranking"]["avg_time"]
            if rank_time > 0.2:
                recommendations.append(
                    "Ranking is slow. Consider algorithm optimization."
                )

        return recommendations

    def clear_profiles(self):
        """Clear all profiles"""
        self.profiles.clear()
        self.current_profile = None
        self.stats = {
            "total_queries": 0,
            "avg_duration": 0.0,
            "cache_hit_rate": 0.0,
            "slow_queries": 0,
            "slow_query_threshold": 1.0,
        }
        self.phase_stats.clear()


# Global profiler instance
_query_profiler: Optional[QueryProfiler] = None


def get_query_profiler() -> QueryProfiler:
    """Get global query profiler instance"""
    global _query_profiler
    if _query_profiler is None:
        _query_profiler = QueryProfiler()
    return _query_profiler
