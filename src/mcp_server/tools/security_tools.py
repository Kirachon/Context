"""
Security & Audit MCP Tools (Epic 4)

Manage roles and record audit events.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.security.authz import set_role, get_role, Roles
from src.security.audit import record_event, read_events


def register_security_tools(mcp: FastMCP):
    @mcp.tool()
    async def security_set_role(role: str) -> Dict[str, Any]:
        set_role(role)
        record_event("set_role", "system", {"role": role})
        return {
            "success": True,
            "role": get_role(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def security_get_role() -> Dict[str, Any]:
        return {
            "success": True,
            "role": get_role(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def audit_list(limit: int = 50) -> Dict[str, Any]:
        events = read_events(limit)
        return {
            "success": True,
            "events": events,
            "count": len(events),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

