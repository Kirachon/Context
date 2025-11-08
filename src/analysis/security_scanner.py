from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Dict, List


SUSPICIOUS = [
    ("S001", "Use of eval()", "eval("),
    ("S002", "Use of exec()", "exec("),
    ("S010", "Subprocess Popen", "subprocess.Popen("),
]


@dataclass
class SecurityIssue:
    line: int
    col: int
    code: str
    message: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class SecurityScanner:
    """Heuristic security scanner (regex-free for speed and safety)."""

    def scan_file(self, path: str) -> Dict[str, object]:
        issues: List[SecurityIssue] = []
        try:
            if not os.path.exists(path):
                return {"success": False, "error": "file_not_found", "issues": []}
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    low = line.lower()
                    for code, msg, needle in SUSPICIOUS:
                        idx = low.find(needle.lower())
                        if idx != -1:
                            issues.append(SecurityIssue(i, idx + 1, code, msg))
        except Exception as e:
            return {"success": False, "error": str(e), "issues": []}

        return {"success": True, "issues": [x.to_dict() for x in issues]}

