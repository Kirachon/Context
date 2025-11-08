"""
MCP tools instrumentation helpers.

Wrap MCP tool functions to capture metrics and latencies.
"""

from __future__ import annotations

import time
from typing import Callable, Any
from src.monitoring.metrics import metrics
from src.config.settings import settings
from src.monitoring.memory_tracker import MemoryTracker


def instrument_tool(name: str):
    """Decorator to instrument an MCP tool with metrics.

    Records:
    - mcp_tool_calls_total{tool, status}
    - mcp_tool_seconds (histogram)

    Note: FastMCP doesn't support *args in tool functions, so we need
    to apply instrumentation without using *args.
    """
    c_calls = metrics.counter(
        "mcp_tool_calls_total", "MCP tool invocations", ("tool", "status")
    )
    h_secs = metrics.histogram("mcp_tool_seconds", "MCP tool latency", ("tool",))

    def decorator(fn):
        # For FastMCP compatibility, we need to preserve the original function signature
        # and type hints exactly. We'll use functools.wraps to ensure all metadata is preserved.
        import functools
        import inspect
        import random

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            mt: MemoryTracker | None = None
            # Optional lightweight memory profiling (feature-flagged)
            if settings.enable_performance_profiling and random.random() < float(settings.profiling_sample_rate):
                try:
                    mt = MemoryTracker()
                    mt.start()
                except Exception:
                    mt = None
            try:
                # Since FastMCP passes named arguments, we can safely forward them
                res = await fn(*args, **kwargs)
                try:
                    h_secs.labels(name).observe(time.perf_counter() - t0)
                    c_calls.labels(name, "ok").inc()
                except Exception:
                    pass
                return res
            except Exception:
                try:
                    h_secs.labels(name).observe(time.perf_counter() - t0)
                    c_calls.labels(name, "error").inc()
                except Exception:
                    pass
                raise
            finally:
                if mt is not None:
                    try:
                        _ = mt.stop()
                        # We intentionally do not alter tool return payloads.
                        # Memory stats can be exported via metrics or logs in the future.
                    except Exception:
                        pass

        # Ensure wrapper has the same signature as the original function
        wrapper.__signature__ = inspect.signature(fn)

        return wrapper

    return decorator
