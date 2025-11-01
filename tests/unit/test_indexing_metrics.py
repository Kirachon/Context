"""
Unit tests for Indexing Metrics (Story 2-7, Phase 2)
"""

import pytest
import time
from src.indexing.indexing_metrics import IndexingMetricsCollector, get_indexing_metrics


@pytest.fixture
def metrics_collector():
    """Create a metrics collector instance"""
    return IndexingMetricsCollector(max_history=100)


def test_metrics_initialization(metrics_collector):
    """Test metrics collector initialization"""
    assert metrics_collector.max_history == 100
    assert len(metrics_collector.batch_history) == 0
    assert metrics_collector.stats["total_batches"] == 0


def test_start_batch(metrics_collector):
    """Test starting a batch"""
    batch_id = metrics_collector.start_batch(batch_size=10)

    assert batch_id == 1
    assert len(metrics_collector.batch_history) == 1


def test_complete_batch(metrics_collector):
    """Test completing a batch"""
    batch_id = metrics_collector.start_batch(batch_size=10)
    time.sleep(0.1)  # Simulate processing time
    metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    assert metrics_collector.stats["total_batches"] == 1
    assert metrics_collector.stats["total_files_processed"] == 10
    assert metrics_collector.stats["total_files_failed"] == 0


def test_batch_with_failures(metrics_collector):
    """Test batch with failed files"""
    batch_id = metrics_collector.start_batch(batch_size=10)
    metrics_collector.complete_batch(batch_id, files_processed=8, files_failed=2)

    assert metrics_collector.stats["total_files_processed"] == 8
    assert metrics_collector.stats["total_files_failed"] == 2


def test_success_rate_calculation(metrics_collector):
    """Test success rate calculation"""
    batch_id1 = metrics_collector.start_batch(batch_size=10)
    metrics_collector.complete_batch(batch_id1, files_processed=10, files_failed=0)

    batch_id2 = metrics_collector.start_batch(batch_size=10)
    metrics_collector.complete_batch(batch_id2, files_processed=8, files_failed=2)

    stats = metrics_collector.get_statistics()

    assert stats["success_rate"] == 90.0  # 18/20 = 90%


def test_throughput_calculation(metrics_collector):
    """Test throughput calculation"""
    batch_id = metrics_collector.start_batch(batch_size=10)
    time.sleep(0.1)
    metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    stats = metrics_collector.get_statistics()

    # Throughput should be approximately 100 files/second (10 files / 0.1 seconds)
    assert stats["avg_throughput"] > 50  # At least 50 files/second


def test_batch_history_limit(metrics_collector):
    """Test batch history respects max size"""
    metrics_collector.max_history = 5

    for i in range(10):
        batch_id = metrics_collector.start_batch(batch_size=10)
        metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    assert len(metrics_collector.batch_history) <= 5


def test_get_batch_history(metrics_collector):
    """Test getting batch history"""
    for i in range(5):
        batch_id = metrics_collector.start_batch(batch_size=10)
        metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    history = metrics_collector.get_batch_history(limit=3)

    assert len(history) == 3
    assert all("batch_id" in b for b in history)
    assert all("throughput" in b for b in history)


def test_optimal_batch_size(metrics_collector):
    """Test optimal batch size determination"""
    # Simulate batches with different sizes
    for size in [5, 10, 15, 20]:
        batch_id = metrics_collector.start_batch(batch_size=size)
        time.sleep(0.05)
        metrics_collector.complete_batch(batch_id, files_processed=size, files_failed=0)

    optimal = metrics_collector.get_optimal_batch_size()

    assert optimal in [5, 10, 15, 20]


def test_performance_trend(metrics_collector):
    """Test performance trend analysis"""
    # Simulate improving performance
    for i in range(5):
        batch_id = metrics_collector.start_batch(batch_size=10)
        time.sleep(0.05 - i * 0.01)  # Decreasing time = improving performance
        metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    trend = metrics_collector.get_performance_trend()

    assert "trend" in trend
    assert "recent_throughputs" in trend
    assert "avg_throughput" in trend


def test_clear_history(metrics_collector):
    """Test clearing metrics history"""
    batch_id = metrics_collector.start_batch(batch_size=10)
    metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    assert metrics_collector.stats["total_batches"] == 1

    metrics_collector.clear_history()

    assert metrics_collector.stats["total_batches"] == 0
    assert len(metrics_collector.batch_history) == 0


def test_get_indexing_metrics_singleton():
    """Test global metrics collector singleton"""
    metrics1 = get_indexing_metrics()
    metrics2 = get_indexing_metrics()

    assert metrics1 is metrics2


def test_multiple_batches_statistics(metrics_collector):
    """Test statistics with multiple batches"""
    for i in range(3):
        batch_id = metrics_collector.start_batch(batch_size=10)
        metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    stats = metrics_collector.get_statistics()

    assert stats["total_batches"] == 3
    assert stats["total_files_processed"] == 30
    assert stats["success_rate"] == 100.0


def test_batch_metrics_duration(metrics_collector):
    """Test batch duration calculation"""
    batch_id = metrics_collector.start_batch(batch_size=10)
    time.sleep(0.2)
    metrics_collector.complete_batch(batch_id, files_processed=10, files_failed=0)

    history = metrics_collector.get_batch_history(limit=1)

    assert history[0]["duration"] >= 0.15  # At least 150ms
