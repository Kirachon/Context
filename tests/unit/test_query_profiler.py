"""
Unit tests for Query Performance Profiler (Story 2-7, Phase 3)
"""

import pytest
import time
from src.search.query_profiler import QueryProfiler, get_query_profiler


@pytest.fixture
def profiler():
    """Create a query profiler"""
    return QueryProfiler(max_history=100)


def test_profiler_initialization(profiler):
    """Test profiler initialization"""
    assert profiler.max_history == 100
    assert len(profiler.profiles) == 0
    assert profiler.stats["total_queries"] == 0


def test_start_query(profiler):
    """Test starting query profiling"""
    profile = profiler.start_query("SELECT * FROM users")

    assert profile.query == "SELECT * FROM users"
    assert profile.start_time is not None
    assert profiler.current_profile is profile


def test_end_query(profiler):
    """Test ending query profiling"""
    profiler.start_query("SELECT * FROM users")
    time.sleep(0.1)
    profiler.end_query(results_count=10, cache_hit=False)

    assert len(profiler.profiles) == 1
    assert profiler.profiles[0].results_count == 10
    assert profiler.profiles[0].cache_hit is False
    assert profiler.profiles[0].total_duration >= 0.1


def test_record_phase(profiler):
    """Test recording query phases"""
    profiler.start_query("SELECT * FROM users")
    profiler.record_phase("parsing", 0.01)
    profiler.record_phase("vector_search", 0.05)
    profiler.record_phase("ranking", 0.02)
    profiler.end_query(results_count=10)

    profile = profiler.profiles[0]
    assert profile.parsing_time == 0.01
    assert profile.vector_search_time == 0.05
    assert profile.ranking_time == 0.02


def test_phase_statistics(profiler):
    """Test phase statistics tracking"""
    for i in range(3):
        profiler.start_query(f"query_{i}")
        profiler.record_phase("parsing", 0.01)
        profiler.record_phase("vector_search", 0.05)
        profiler.end_query(results_count=10)

    stats = profiler.get_statistics()

    assert stats["phase_stats"]["parsing"]["count"] == 3
    assert stats["phase_stats"]["vector_search"]["count"] == 3


def test_cache_hit_rate(profiler):
    """Test cache hit rate calculation"""
    # 3 cache hits, 2 misses
    for i in range(3):
        profiler.start_query(f"query_{i}")
        profiler.end_query(results_count=10, cache_hit=True)

    for i in range(2):
        profiler.start_query(f"query_{i+3}")
        profiler.end_query(results_count=10, cache_hit=False)

    stats = profiler.get_statistics()

    assert stats["cache_hit_rate"] == 60.0  # 3/5 = 60%


def test_slow_queries_detection(profiler):
    """Test slow query detection"""
    # Fast query
    profiler.start_query("fast_query")
    time.sleep(0.1)
    profiler.end_query(results_count=10)

    # Slow query (exceeds 1.0 second threshold)
    profiler.start_query("slow_query")
    time.sleep(1.1)
    profiler.end_query(results_count=10)

    stats = profiler.get_statistics()

    assert stats["slow_queries"] == 1


def test_get_slow_queries(profiler):
    """Test getting slowest queries"""
    for i in range(5):
        profiler.start_query(f"query_{i}")
        time.sleep(0.01 * (i + 1))  # Increasing duration
        profiler.end_query(results_count=10)

    slow_queries = profiler.get_slow_queries(limit=3)

    assert len(slow_queries) == 3
    # Should be sorted by duration (descending)
    assert slow_queries[0]["duration"] >= slow_queries[1]["duration"]


def test_optimization_recommendations_low_cache_hit(profiler):
    """Test recommendations for low cache hit rate"""
    for i in range(10):
        profiler.start_query(f"query_{i}")
        profiler.end_query(results_count=10, cache_hit=(i < 2))  # Only 20% hit rate

    recommendations = profiler.get_optimization_recommendations()

    assert any("cache" in r.lower() for r in recommendations)


def test_optimization_recommendations_slow_vector_search(profiler):
    """Test recommendations for slow vector search"""
    for i in range(5):
        profiler.start_query(f"query_{i}")
        profiler.record_phase("vector_search", 0.6)  # Slow
        profiler.end_query(results_count=10)

    recommendations = profiler.get_optimization_recommendations()

    assert any("vector search" in r.lower() for r in recommendations)


def test_profile_history_limit(profiler):
    """Test profile history respects max size"""
    profiler.max_history = 5

    for i in range(10):
        profiler.start_query(f"query_{i}")
        profiler.end_query(results_count=10)

    assert len(profiler.profiles) <= 5


def test_get_statistics(profiler):
    """Test getting statistics"""
    for i in range(3):
        profiler.start_query(f"query_{i}")
        time.sleep(0.05)
        profiler.end_query(results_count=10)

    stats = profiler.get_statistics()

    assert stats["total_queries"] == 3
    assert stats["avg_duration"] > 0
    assert "phase_stats" in stats


def test_clear_profiles(profiler):
    """Test clearing profiles"""
    profiler.start_query("query_1")
    profiler.end_query(results_count=10)

    assert len(profiler.profiles) == 1

    profiler.clear_profiles()

    assert len(profiler.profiles) == 0
    assert profiler.stats["total_queries"] == 0


def test_get_query_profiler_singleton():
    """Test global query profiler singleton"""
    profiler1 = get_query_profiler()
    profiler2 = get_query_profiler()

    assert profiler1 is profiler2


def test_multiple_phases_same_query(profiler):
    """Test recording multiple instances of same phase"""
    profiler.start_query("query_1")
    profiler.record_phase("parsing", 0.01)
    profiler.record_phase("parsing", 0.02)  # Second parsing phase
    profiler.end_query(results_count=10)

    profile = profiler.profiles[0]
    assert profile.parsing_time == 0.03  # 0.01 + 0.02


def test_average_duration_calculation(profiler):
    """Test average duration calculation"""
    for i in range(3):
        profiler.start_query(f"query_{i}")
        time.sleep(0.05)
        profiler.end_query(results_count=10)

    stats = profiler.get_statistics()

    assert stats["avg_duration"] >= 0.05
