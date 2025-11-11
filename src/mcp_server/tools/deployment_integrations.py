"""
Deployment Integrations MCP Tools

Safe, feature-flagged wrappers for common deployment platforms:
- Vercel
- Render
- Railway
- Supabase

Design:
- Dynamic imports with graceful degradation (no hard deps)
- Return structured result with success flag; never raise for missing SDKs
- Pure MCP tools; no side effects unless called
"""
from __future__ import annotations

import sys
import os
from typing import Any, Dict, Optional

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.mcp_server.tools.instrumentation import instrument_tool


def _sdk_available(pkg_name: str) -> bool:
    try:
        __import__(pkg_name)
        return True
    except Exception:
        return False


def register_deployment_tools(mcp: FastMCP):
    """Register deployment integration tools on the given MCP server."""

    @mcp.tool()
    @instrument_tool("deploy_to_vercel")
    async def deploy_to_vercel(repo_url: str, project_id: Optional[str] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
        if not _sdk_available("vercel"):
            return {
                "success": False,
                "provider": "vercel",
                "error": "Vercel SDK not installed. Install optional deps from requirements/integrations.txt.",
            }
        # NOTE: Actual implementation can use official SDK; kept minimal for safety.
        # This endpoint acts as a placeholder to be mocked in tests and wired up when deps are installed.
        return {
            "success": True,
            "provider": "vercel",
            "message": "Deployment request accepted (mock).",
            "project_id": project_id,
            "team_id": team_id,
            "repo_url": repo_url,
        }

    @mcp.tool()
    @instrument_tool("deploy_to_render")
    async def deploy_to_render(repo_url: str, service_id: Optional[str] = None) -> Dict[str, Any]:
        if not _sdk_available("render") and not _sdk_available("render_python") and not _sdk_available("render-python"):
            return {
                "success": False,
                "provider": "render",
                "error": "Render SDK not installed. Install optional deps from requirements/integrations.txt.",
            }
        return {
            "success": True,
            "provider": "render",
            "message": "Deployment request accepted (mock).",
            "service_id": service_id,
            "repo_url": repo_url,
        }

    @mcp.tool()
    @instrument_tool("deploy_to_railway")
    async def deploy_to_railway(repo_url: str, project_id: Optional[str] = None, service: Optional[str] = None) -> Dict[str, Any]:
        if not _sdk_available("railway"):
            return {
                "success": False,
                "provider": "railway",
                "error": "Railway SDK not installed. Install optional deps from requirements/integrations.txt.",
            }
        return {
            "success": True,
            "provider": "railway",
            "message": "Deployment request accepted (mock).",
            "project_id": project_id,
            "service": service,
            "repo_url": repo_url,
        }

    @mcp.tool()
    @instrument_tool("deploy_to_supabase")
    async def deploy_to_supabase(project_ref: str, migration_dir: Optional[str] = None) -> Dict[str, Any]:
        if not _sdk_available("supabase") and not _sdk_available("supabase_py"):
            return {
                "success": False,
                "provider": "supabase",
                "error": "Supabase SDK not installed. Install optional deps from requirements/integrations.txt.",
            }
        return {
            "success": True,
            "provider": "supabase",
            "message": "Deployment request accepted (mock).",
            "project_ref": project_ref,
            "migration_dir": migration_dir,
        }

