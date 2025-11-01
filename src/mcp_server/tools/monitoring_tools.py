"""
Monitoring & Alerting MCP Tools (Epic 4)

Expose simple alerts registry and basic metrics.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.monitoring.alerts import emit_alert, list_alerts, clear_alerts
from src.monitoring.metrics import metrics
from src.security.authz import require_role, Roles
from src.security.audit import record_event
from src.mcp_server.tools.instrumentation import instrument_tool


def register_monitoring_tools(mcp: FastMCP):
    @mcp.tool()
    @instrument_tool("alerts_emit")
    async def alerts_emit(key: str, level: str, message: str) -> Dict[str, Any]:
        emit_alert(key, level, message)
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("alerts_list")
    async def alerts_list(limit: int = 50) -> Dict[str, Any]:
        alerts = list_alerts(limit)
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("alerts_clear")
    @require_role([Roles.ADMIN])
    async def alerts_clear() -> Dict[str, Any]:
        clear_alerts()
        record_event("alerts_clear", "mcp", {"actor_role": Roles.ADMIN})
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    @mcp.tool()
    @instrument_tool("metrics_summary")
    async def metrics_summary() -> Dict[str, Any]:
        # Minimal snapshot of defined metrics (in-process or prometheus-backed)
        try:
            counters = list(getattr(metrics, "_counters", {}).keys())
            histograms = list(getattr(metrics, "_hists", {}).keys())
        except Exception:
            counters, histograms = [], []
        return {
            "success": True,
            "counters": counters,
            "histograms": histograms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


