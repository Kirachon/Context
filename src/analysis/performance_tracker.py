from __future__ import annotations

from typing import Dict
from collections import defaultdict


class PerformanceTracker:
    """In-memory tracker for simple performance counters.

    Not persisted; intended for quick inspection/tests.
    """

    def __init__(self) -> None:
        self._durations_ms: Dict[str, float] = defaultdict(float)
        self._counts: Dict[str, int] = defaultdict(int)

    def record(self, file_path: str, duration_ms: float) -> None:
        self._durations_ms[file_path] += float(duration_ms)
        self._counts[file_path] += 1

    def get_summary(self) -> Dict[str, object]:
        totals = sum(self._durations_ms.values())
        count = sum(self._counts.values())
        avg = (totals / count) if count else 0.0
        return {
            "total_files": len(self._counts),
            "total_events": count,
            "avg_duration_ms": avg,
        }


# Global instance
perf_tracker = PerformanceTracker()

