from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

try:  # Python 3.10+
    from importlib.metadata import distributions
except Exception:  # pragma: no cover
    from importlib_metadata import distributions  # type: ignore


@dataclass
class PackageInfo:
    name: str
    version: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class DependencyIssue:
    package: str
    version: str
    severity: str
    cve: str
    description: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


class DependencyChecker:
    """Lightweight dependency checker.

    Without external services, we can enumerate installed packages; CVE checks
    require external tools and are intentionally omitted here for safety.
    """

    def list_installed(self) -> List[PackageInfo]:
        pkgs: List[PackageInfo] = []
        for dist in distributions():
            name = getattr(dist.metadata, "get", lambda k, d=None: d)("Name", None) or getattr(dist, "metadata", {}).get("Name", "")
            version = getattr(dist.metadata, "get", lambda k, d=None: d)("Version", None) or getattr(dist, "version", "")
            if name:
                pkgs.append(PackageInfo(name=name, version=str(version)))
        return pkgs

    def find_vulnerabilities(self) -> List[DependencyIssue]:
        # Placeholder: without safety/pip-audit, we don't fetch CVEs.
        return []

