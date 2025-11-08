from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class QualityIssue:
    line: int
    col: int
    code: str
    message: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class CodeQualityAnalyzer:
    """Lightweight analyzer using simple heuristics (no external deps)."""

    def __init__(self, max_line_length: int = 120):
        self.max_line_length = max_line_length

    def analyze_file(self, path: str) -> Dict[str, object]:
        issues: List[QualityIssue] = []
        try:
            if not os.path.exists(path):
                return {"success": False, "error": "file_not_found", "issues": []}
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    # Line length
                    if len(line.rstrip("\n")) > self.max_line_length:
                        issues.append(
                            QualityIssue(i, self.max_line_length, "Q001", f"Line exceeds {self.max_line_length} chars")
                        )
                    # TODOs
                    if "TODO" in line:
                        col = line.index("TODO") + 1
                        issues.append(QualityIssue(i, col, "Q100", "TODO left in code"))
        except Exception as e:
            return {"success": False, "error": str(e), "issues": []}

        return {"success": True, "issues": [x.to_dict() for x in issues]}

