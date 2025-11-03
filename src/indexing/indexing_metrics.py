"""
Indexing Performance Metrics (Story 2-7, Phase 2)

Tracks and reports indexing performance metrics for optimization.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    """Metrics for a single indexing batch"""

    batch_id: int
    batch_size: int
    start_time: datetime
    end_time: datetime = None
    files_processed: int = 0
    files_failed: int = 0
    total_duration: float = 0.0

    def complete(self):
        """Mark batch as complete"""
        self.end_time = datetime.now(timezone.utc)
        self.total_duration = (self.end_time - self.start_time).total_seconds()


class IndexingMetricsCollector:
    """
    Collects and analyzes indexing performance metrics

    Tracks:
    - Batch processing times
    - Throughput (files per second)
    - Success/failure rates
    - Performance trends
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector

        Args:
            max_history: Maximum number of batches to keep in history
        """
        self.max_history = max_history
        self.batch_history: List[BatchMetrics] = []
        self.current_batch_id = 0

        # Statistics
        self.stats = {
            "total_batches": 0,
            "total_files_processed": 0,
            "total_files_failed": 0,
            "total_duration": 0.0,
            "avg_batch_time": 0.0,
            "avg_throughput": 0.0,  # files per second
            "success_rate": 0.0,
        }

        # Performance by batch size
        self.performance_by_batch_size: Dict[int, List[float]] = defaultdict(list)

    def start_batch(self, batch_size: int) -> int:
        """
        Start tracking a new batch

        Args:
            batch_size: Number of files in batch

        Returns:
            Batch ID
        """
        self.current_batch_id += 1
        batch = BatchMetrics(
            batch_id=self.current_batch_id,
            batch_size=batch_size,
            start_time=datetime.now(timezone.utc),
        )
        self.batch_history.append(batch)

        # Keep history size under control
        if len(self.batch_history) > self.max_history:
            self.batch_history.pop(0)

        return self.current_batch_id

    def complete_batch(
        self, batch_id: int, files_processed: int, files_failed: int = 0
    ):
        """
        Mark batch as complete

        Args:
            batch_id: ID of batch to complete
            files_processed: Number of files successfully processed
            files_failed: Number of files that failed
        """
        # Find batch
        batch = None
        for b in self.batch_history:
            if b.batch_id == batch_id:
                batch = b
                break

        if not batch:
            logger.warning(f"Batch {batch_id} not found")
            return

        # Update batch
        batch.files_processed = files_processed
        batch.files_failed = files_failed
        batch.complete()

        # Update statistics
        self.stats["total_batches"] += 1
        self.stats["total_files_processed"] += files_processed
        self.stats["total_files_failed"] += files_failed
        self.stats["total_duration"] += batch.total_duration

        # Track performance by batch size
        throughput = (
            files_processed / batch.total_duration if batch.total_duration > 0 else 0
        )
        self.performance_by_batch_size[batch.batch_size].append(throughput)

        # Update averages
        self._update_statistics()

        logger.debug(
            f"Batch {batch_id} complete: "
            f"{files_processed} processed, {files_failed} failed, "
            f"{batch.total_duration:.2f}s"
        )

    def _update_statistics(self):
        """Update aggregate statistics"""
        if self.stats["total_batches"] > 0:
            self.stats["avg_batch_time"] = (
                self.stats["total_duration"] / self.stats["total_batches"]
            )

        total_files = (
            self.stats["total_files_processed"] + self.stats["total_files_failed"]
        )
        if total_files > 0:
            self.stats["success_rate"] = (
                self.stats["total_files_processed"] / total_files * 100
            )

        if self.stats["total_duration"] > 0:
            self.stats["avg_throughput"] = (
                self.stats["total_files_processed"] / self.stats["total_duration"]
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            "total_batches": self.stats["total_batches"],
            "total_files_processed": self.stats["total_files_processed"],
            "total_files_failed": self.stats["total_files_failed"],
            "total_duration": round(self.stats["total_duration"], 2),
            "avg_batch_time": round(self.stats["avg_batch_time"], 2),
            "avg_throughput": round(self.stats["avg_throughput"], 2),
            "success_rate": round(self.stats["success_rate"], 2),
        }

    def get_batch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent batch history

        Args:
            limit: Maximum number of batches to return

        Returns:
            List of batch metrics
        """
        recent = self.batch_history[-limit:]
        return [
            {
                "batch_id": b.batch_id,
                "batch_size": b.batch_size,
                "files_processed": b.files_processed,
                "files_failed": b.files_failed,
                "duration": round(b.total_duration, 2),
                "throughput": round(
                    b.files_processed / b.total_duration if b.total_duration > 0 else 0,
                    2,
                ),
            }
            for b in recent
        ]

    def get_optimal_batch_size(self) -> int:
        """
        Determine optimal batch size based on performance data

        Returns:
            Recommended batch size
        """
        if not self.performance_by_batch_size:
            return 10  # Default

        # Find batch size with highest throughput
        best_size = 10
        best_throughput = 0

        for batch_size, throughputs in self.performance_by_batch_size.items():
            avg_throughput = sum(throughputs) / len(throughputs)
            if avg_throughput > best_throughput:
                best_throughput = avg_throughput
                best_size = batch_size

        return best_size

    def get_performance_trend(self, window_size: int = 10) -> Dict[str, Any]:
        """
        Get performance trend over recent batches

        Args:
            window_size: Number of recent batches to analyze

        Returns:
            Trend analysis
        """
        recent = self.batch_history[-window_size:]

        if not recent:
            return {"trend": "no_data"}

        throughputs = [
            b.files_processed / b.total_duration if b.total_duration > 0 else 0
            for b in recent
        ]

        # Calculate trend
        if len(throughputs) >= 2:
            first_half = sum(throughputs[: len(throughputs) // 2]) / (
                len(throughputs) // 2
            )
            second_half = sum(throughputs[len(throughputs) // 2 :]) / (
                len(throughputs) - len(throughputs) // 2
            )

            if second_half > first_half * 1.1:
                trend = "improving"
            elif second_half < first_half * 0.9:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "recent_throughputs": [round(t, 2) for t in throughputs],
            "avg_throughput": round(sum(throughputs) / len(throughputs), 2),
        }

    def clear_history(self):
        """Clear all metrics history"""
        self.batch_history.clear()
        self.stats = {
            "total_batches": 0,
            "total_files_processed": 0,
            "total_files_failed": 0,
            "total_duration": 0.0,
            "avg_batch_time": 0.0,
            "avg_throughput": 0.0,
            "success_rate": 0.0,
        }
        self.performance_by_batch_size.clear()


# Global metrics collector instance
_metrics_collector: IndexingMetricsCollector = None


def get_indexing_metrics() -> IndexingMetricsCollector:
    """Get global indexing metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = IndexingMetricsCollector()
    return _metrics_collector


# The IndexingMetrics class is provided through IndexingMetricsCollector above
# This is a wrapper class for convenience in MCP tool integration
class IndexingMetrics:
    """
    Convenience wrapper for indexing metrics.

    Provides basic methods for accessing metrics data.
    """

    def __init__(self):
        """Initialize IndexingMetrics wrapper."""
        self.collector = get_indexing_metrics()

    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        return self.collector.get_statistics()

    def get_batch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent batch history."""
        return self.collector.get_batch_history(limit)

    def get_optimal_batch_size(self) -> int:
        """Get optimal batch size."""
        return self.collector.get_optimal_batch_size()


# Module-level stub function for MCP tool integration
def get_metrics() -> Dict:
    """
    Get indexing metrics.

    Stub implementation for MCP tool integration.

    Returns:
        Dict with status and metrics data
    """
    logger.warning("IndexingMetrics stub called")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "get_metrics is a stub implementation",
        "results": [],
        "metrics": {},
        "data": {}
    }
