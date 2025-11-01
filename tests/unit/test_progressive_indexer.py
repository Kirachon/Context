"""
Unit tests for Progressive Indexer (Story 2-7, Phase 2)
"""

import pytest
from src.indexing.progressive_indexer import (
    ProgressiveIndexer,
    IndexingTask,
    IndexingPriority,
    get_progressive_indexer,
)


@pytest.fixture
def indexer():
    """Create a progressive indexer instance"""
    return ProgressiveIndexer(
        initial_batch_size=10, max_batch_size=50, min_batch_size=1
    )


def test_indexer_initialization(indexer):
    """Test indexer initialization"""
    assert indexer.initial_batch_size == 10
    assert indexer.max_batch_size == 50
    assert indexer.min_batch_size == 1
    assert indexer.current_batch_size == 10
    assert indexer.total_tasks == 0
    assert indexer.completed_tasks == 0


def test_add_single_task(indexer):
    """Test adding a single task"""
    indexer.add_task("file1.py", IndexingPriority.NORMAL)

    assert indexer.total_tasks == 1
    assert len(indexer.task_queue) == 1


def test_add_multiple_tasks(indexer):
    """Test adding multiple tasks"""
    files = ["file1.py", "file2.py", "file3.py"]
    indexer.add_tasks_batch(files, IndexingPriority.NORMAL)

    assert indexer.total_tasks == 3
    assert len(indexer.task_queue) == 3


def test_task_priority_ordering(indexer):
    """Test that tasks are ordered by priority"""
    indexer.add_task("file1.py", IndexingPriority.LOW)
    indexer.add_task("file2.py", IndexingPriority.CRITICAL)
    indexer.add_task("file3.py", IndexingPriority.HIGH)

    batch = indexer.get_next_batch()

    # First task should be CRITICAL
    assert batch[0].priority == IndexingPriority.CRITICAL


def test_get_next_batch(indexer):
    """Test getting next batch"""
    files = [f"file{i}.py" for i in range(25)]
    indexer.add_tasks_batch(files, IndexingPriority.NORMAL)

    batch = indexer.get_next_batch()

    assert len(batch) == 10  # initial_batch_size
    assert len(indexer.task_queue) == 15


def test_mark_completed(indexer):
    """Test marking task as completed"""
    indexer.add_task("file1.py", IndexingPriority.NORMAL)
    task = indexer.task_queue[0]

    indexer.mark_completed(task)

    assert indexer.completed_tasks == 1


def test_mark_failed_with_retry(indexer):
    """Test marking task as failed with retry"""
    indexer.add_task("file1.py", IndexingPriority.NORMAL)
    task = indexer.task_queue[0]

    indexer.mark_failed(task, "Test error")

    # Task should be re-queued
    assert indexer.failed_tasks == 0
    assert len(indexer.task_queue) == 1
    assert indexer.task_queue[0].retry_count == 1


def test_mark_failed_max_retries(indexer):
    """Test marking task as failed after max retries"""
    indexer.add_task("file1.py", IndexingPriority.NORMAL)
    task = indexer.task_queue[0]
    task.max_retries = 1

    indexer.mark_failed(task, "Test error")
    indexer.mark_failed(task, "Test error")

    assert indexer.failed_tasks == 1


def test_pause_resume(indexer):
    """Test pause and resume"""
    assert indexer.paused is False

    indexer.pause()
    assert indexer.paused is True

    indexer.resume()
    assert indexer.paused is False


def test_get_progress(indexer):
    """Test getting progress"""
    indexer.add_tasks_batch(["file1.py", "file2.py", "file3.py"])
    indexer.completed_tasks = 1

    progress = indexer.get_progress()

    assert progress["total_tasks"] == 3
    assert progress["completed_tasks"] == 1
    assert progress["progress_percent"] == pytest.approx(33.33, 0.1)


def test_get_metrics(indexer):
    """Test getting metrics"""
    indexer.add_tasks_batch(["file1.py", "file2.py"])

    metrics = indexer.get_metrics()

    assert "total_tasks" in metrics
    assert "completed_tasks" in metrics
    assert "metrics" in metrics


def test_get_progressive_indexer_singleton():
    """Test global progressive indexer singleton"""
    indexer1 = get_progressive_indexer()
    indexer2 = get_progressive_indexer()

    assert indexer1 is indexer2


def test_indexing_task_comparison():
    """Test task priority comparison"""
    task1 = IndexingTask("file1.py", IndexingPriority.HIGH)
    task2 = IndexingTask("file2.py", IndexingPriority.LOW)

    assert task1 < task2  # HIGH priority < LOW priority


def test_batch_size_limits(indexer):
    """Test batch size respects limits"""
    indexer.current_batch_size = 100  # Try to exceed max
    indexer.adapt_batch_size()

    # Should not exceed max_batch_size
    assert indexer.current_batch_size <= indexer.max_batch_size
