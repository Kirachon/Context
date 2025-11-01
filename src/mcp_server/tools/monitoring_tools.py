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
from src.monitoring.metrics import get_metrics if False else None  # placeholder if metrics provide accessor


def register_monitoring_tools(mcp: FastMCP):
    @mcp.tool()
    async def alerts_emit(key: str, level: str, message: str) -> Dict[str, Any]:
        emit_alert(key, level, message)
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def alerts_list(limit: int = 50) -> Dict[str, Any]:
        alerts = list_alerts(limit)
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def alerts_clear() -> Dict[str, Any]:
        clear_alerts()
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

