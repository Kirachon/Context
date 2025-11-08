from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

from .vulnerability_scanner import Finding
from .dependency_checker import DependencyIssue


@dataclass
class ComplianceReport:
    summary: Dict[str, int]
    vulnerabilities: List[Dict]
    dependency_issues: List[Dict]

    def to_dict(self) -> Dict:
        return asdict(self)


class ComplianceReporter:
    def generate(self, vulns: List[Finding], dep_issues: List[DependencyIssue]) -> ComplianceReport:
        sev_counts = {"low": 0, "medium": 0, "high": 0}
        for v in vulns:
            sev_counts[v.severity] = sev_counts.get(v.severity, 0) + 1
        return ComplianceReport(
            summary={
                "total_vulnerabilities": len(vulns),
                "low": sev_counts.get("low", 0),
                "medium": sev_counts.get("medium", 0),
                "high": sev_counts.get("high", 0),
                "dependency_issues": len(dep_issues),
            },
            vulnerabilities=[v.to_dict() for v in vulns],
            dependency_issues=[d.to_dict() for d in dep_issues],
        )

