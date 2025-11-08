from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Optional


@dataclass
class ProfileResult:
    label: str
    duration_ms: float
    started_at: float
    finished_at: float
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Profiler:
    """Lightweight profiler using time.perf_counter().

    No external dependencies. Suitable for sampling-based profiling on MCP tools.
    """

    def __init__(self, label: str = "operation"):
        self.label = label
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None
        self._extra: Dict[str, Any] = {}

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    def start(self):
        self._t0 = time.perf_counter()
        self._extra["started_wall_time"] = time.time()
        return self

    def stop(self) -> ProfileResult:
        self._t1 = time.perf_counter()
        started_at = self._extra.get("started_wall_time", time.time())
        finished_at = time.time()
        dur_ms = (self._t1 - (self._t0 or self._t1)) * 1000.0
        return ProfileResult(
            label=self.label,
            duration_ms=dur_ms,
            started_at=started_at,
            finished_at=finished_at,
            extra=dict(self._extra),
        )

    def profile_function(self, fn: Callable, *args, **kwargs) -> ProfileResult:
        self.start()
        try:
            _ = fn(*args, **kwargs)
        finally:
            return self.stop()

