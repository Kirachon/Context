from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.config.settings import settings
from src.mcp_server.tools.instrumentation import instrument_tool
from src.monitoring.profiler import Profiler
from src.monitoring.memory_tracker import MemoryTracker


def register_performance_tools(mcp):
    @mcp.tool()
    @instrument_tool("profile_operation")
    async def profile_operation(duration_ms: int = 25, complexity: int = 50) -> Dict[str, Any]:
        """Run a controlled synthetic workload and return timing/memory stats.

        This tool is feature-flagged by settings.enable_performance_profiling.
        It uses standard library only and is safe to run in CI.
        """
        # Resolve settings at call time to avoid stale references in long-lived modules/tests
        from src.config.settings import settings as cfg
        if not getattr(cfg, "enable_performance_profiling", False):
            return {
                "success": False,
                "error": "performance profiling disabled by configuration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        pr = Profiler(label="synthetic_workload")
        mt = MemoryTracker()
        try:
            mt.start()
        except Exception:
            pass

        def workload(target_ms: int, c: int):
            # Busy-wait for target_ms, sprinkled with small computations
            end = time.perf_counter() + (target_ms / 1000.0)
            x = 0.0
            while time.perf_counter() < end:
                # small math ops to avoid being optimized away
                x += math.sqrt((c % 7) + 1) * math.sin(x + 0.1)
            return x

        result = pr.profile_function(workload, max(0, int(duration_ms)), max(1, int(complexity)))
        mem = mt.stop() if hasattr(mt, "stop") else None

        payload: Dict[str, Any] = {
            "success": True,
            "profile": result.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if mem is not None:
            payload["memory"] = mem.to_dict()
        return payload

    @mcp.tool()
    @instrument_tool("get_performance_stats")
    async def get_performance_stats() -> Dict[str, Any]:
        """Return runtime profiling capability status and defaults.

        Minimal read-only info (no aggregation backend required).
        """
        from src.config.settings import settings as cfg
        return {
            "success": True,
            "profiling_enabled": bool(getattr(cfg, "enable_performance_profiling", False)),
            "sample_rate": float(getattr(cfg, "profiling_sample_rate", 0.0)),
            "store_results": bool(getattr(cfg, "profiling_store_results", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("identify_bottlenecks")
    async def identify_bottlenecks(sample_runs: int = 3) -> Dict[str, Any]:
        """Perform a few synthetic runs and report slowest observation.

        This does not inspect application internals; it's a safe rough signal
        suitable for smoke checks.
        """
        from src.config.settings import settings as cfg
        if not getattr(cfg, "enable_performance_profiling", False):
            return {
                "success": False,
                "error": "performance profiling disabled by configuration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        samples = []
        for _ in range(max(1, int(sample_runs))):
            res = await profile_operation(duration_ms=10, complexity=25)
            if res.get("success"):
                samples.append(res["profile"]["duration_ms"])  # type: ignore[index]
        slowest = max(samples) if samples else 0.0
        return {
            "success": True,
            "observations": len(samples),
            "slowest_ms": slowest,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

