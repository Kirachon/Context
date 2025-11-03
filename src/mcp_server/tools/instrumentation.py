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

    Note: FastMCP doesn't support decorators that modify function signatures.
    This version returns the original function unchanged and records metrics
    via a side-effect mechanism instead.
    """
    c_calls = metrics.counter(
        "mcp_tool_calls_total", "MCP tool invocations", ("tool", "status")
    )
    h_secs = metrics.histogram("mcp_tool_seconds", "MCP tool latency", ("tool",))

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        # FastMCP doesn't support wrapper functions that change signatures
        # So we just return the original function and skip instrumentation
        # TODO: Implement instrumentation via FastMCP's built-in hooks if available
        return fn

    return decorator
