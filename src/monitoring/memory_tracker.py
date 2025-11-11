from __future__ import annotations

import tracemalloc
from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class MemoryStats:
    current_kb: int
    peak_kb: int

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


class MemoryTracker:
    """Lightweight memory tracker using tracemalloc.

    Works cross-platform and avoids external dependencies.
    """

    def __init__(self):
        self._started = False

    def start(self):
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self._started = True

    def stop(self) -> MemoryStats:
        if not self._started:
            # When not started, return zeros
            return MemoryStats(current_kb=0, peak_kb=0)
        current, peak = tracemalloc.get_traced_memory()
        stats = MemoryStats(current_kb=int(current / 1024), peak_kb=int(peak / 1024))
        tracemalloc.stop()
        self._started = False
        return stats

