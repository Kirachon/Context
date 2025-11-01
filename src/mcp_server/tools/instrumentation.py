"""
MCP tools instrumentation helpers.

Wrap MCP tool functions to capture metrics and latencies.
"""

from __future__ import annotations

import time
from typing import Callable, Any
from src.monitoring.metrics import metrics


def instrument_tool(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to instrument an MCP tool with metrics.

    Records:
    - mcp_tool_calls_total{tool, status}
    - mcp_tool_seconds (histogram)
    """
    c_calls = metrics.counter(
        "mcp_tool_calls_total", "MCP tool invocations", ("tool", "status")
    )
    h_secs = metrics.histogram("mcp_tool_seconds", "MCP tool latency", ("tool",))

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args, **kwargs):  # type: ignore[override]
            t0 = time.perf_counter()
            try:
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

        return wrapper

    return decorator
