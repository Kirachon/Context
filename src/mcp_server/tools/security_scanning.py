from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from src.config.settings import settings
from src.mcp_server.tools.instrumentation import instrument_tool
from src.security.vulnerability_scanner import VulnerabilityScanner
from src.security.dependency_checker import DependencyChecker
from src.security.compliance_reporter import ComplianceReporter


def register_security_scanning_tools(mcp):
    @mcp.tool()
    @instrument_tool("scan_security")
    async def scan_security(root: str = ".") -> Dict[str, Any]:
        """Run lightweight pattern-based security scan over repo (safe-by-default).

        Feature-flagged by settings.enable_security_scanning.
        """
        # Resolve settings at call time to avoid stale references under pytest
        from src.config.settings import settings as cfg
        if not getattr(cfg, "enable_security_scanning", False):
            return {
                "success": False,
                "error": "security scanning disabled by configuration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        scanner = VulnerabilityScanner(root=root)
        vulns = [v.to_dict() for v in scanner.scan()]
        return {
            "success": True,
            "count": len(vulns),
            "vulnerabilities": vulns,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("check_dependencies")
    async def check_dependencies() -> Dict[str, Any]:
        from src.config.settings import settings as cfg
        if not getattr(cfg, "enable_security_scanning", False):
            return {
                "success": False,
                "error": "security scanning disabled by configuration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        dep = DependencyChecker()
        installed = [p.to_dict() for p in dep.list_installed()[:50]]  # limit output
        issues = [i.to_dict() for i in dep.find_vulnerabilities()]
        return {
            "success": True,
            "installed_preview": installed,
            "dependency_issues": issues,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("generate_compliance_report")
    async def generate_compliance_report(root: str = ".") -> Dict[str, Any]:
        from src.config.settings import settings as cfg
        if not getattr(cfg, "enable_security_scanning", False):
            return {
                "success": False,
                "error": "security scanning disabled by configuration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        vulns = VulnerabilityScanner(root=root).scan()
        issues = DependencyChecker().find_vulnerabilities()
        report = ComplianceReporter().generate(vulns, issues)
        return {
            "success": True,
            "report": report.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

