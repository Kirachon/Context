"""
Model Management MCP Tools (Story 5-2)
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.ai_processing.model_manager import get_model_manager
from src.security.authz import require_role, Roles
from src.security.audit import record_event


def register_model_tools(mcp: FastMCP):
    @mcp.tool()
    async def model_list() -> Dict[str, Any]:
        mm = get_model_manager()
        return {
            "success": True,
            "default_model": mm.get_default_model(),
            "models": mm.list_models(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @require_role([Roles.ADMIN])
    async def model_register(name: str) -> Dict[str, Any]:
        mm = get_model_manager()
        mm.register_model(name)
        record_event("model_register", "mcp", {"name": name, "actor_role": Roles.ADMIN})
        return {
            "success": True,
            "models": mm.list_models(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @require_role([Roles.ADMIN])
    async def model_set_default(name: str) -> Dict[str, Any]:
        mm = get_model_manager()
        mm.set_default_model(name)
        record_event("model_set_default", "mcp", {"name": name, "actor_role": Roles.ADMIN})
        return {
            "success": True,
            "default_model": mm.get_default_model(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

