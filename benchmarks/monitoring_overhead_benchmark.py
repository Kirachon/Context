from __future__ import annotations

import time
from statistics import mean

# Use the in-memory PerformanceTracker as stand-in for monitoring callbacks
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.analysis.performance_tracker import perf_tracker


def _work_unit(n: int = 50) -> int:
    s = 0
    for i in range(n):
        s += (i * 31) % 97
    return s


def run(iterations: int = 20000, unit_size: int = 50) -> dict:
    # Baseline (monitoring disabled)
    t0 = time.perf_counter()
    for _ in range(iterations):
        _work_unit(unit_size)
    t1 = time.perf_counter()
    baseline = t1 - t0

    # With monitoring-like overhead (recording a metric)
    t2 = time.perf_counter()
    for _ in range(iterations):
        start = time.perf_counter()
        _work_unit(unit_size)
        dur_ms = (time.perf_counter() - start) * 1000.0
        # Monitoring callback overhead
        perf_tracker.record("synthetic.py", dur_ms)
    t3 = time.perf_counter()
    with_monitoring = t3 - t2

    overhead = with_monitoring - baseline
    pct = (overhead / baseline * 100.0) if baseline > 0 else 0.0
    return {
        "iterations": iterations,
        "unit_size": unit_size,
        "baseline_s": round(baseline, 6),
        "with_monitoring_s": round(with_monitoring, 6),
        "overhead_s": round(overhead, 6),
        "overhead_pct": round(pct, 2),
    }


if __name__ == "__main__":
    result = run()
    print(result)

