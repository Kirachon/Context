from __future__ import annotations

from typing import Dict, Any
from datetime import datetime, timezone
from fastmcp import FastMCP

from src.mcp_server.tools.instrumentation import instrument_tool
from src.analysis.code_quality import CodeQualityAnalyzer
from src.analysis.security_scanner import SecurityScanner
from src.analysis.performance_tracker import perf_tracker


def register_code_monitoring_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    @instrument_tool("analyze_code_quality")
    async def analyze_code_quality(path: str) -> Dict[str, Any]:
        qa = CodeQualityAnalyzer()
        res = qa.analyze_file(path)
        return {**res, "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    @instrument_tool("scan_security_issues")
    async def scan_security_issues(path: str) -> Dict[str, Any]:
        scanner = SecurityScanner()
        res = scanner.scan_file(path)
        return {**res, "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    @instrument_tool("get_quality_trends")
    async def get_quality_trends() -> Dict[str, Any]:
        return {"success": True, "performance": perf_tracker.get_summary(), "timestamp": datetime.now(timezone.utc).isoformat()}

