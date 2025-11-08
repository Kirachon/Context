from __future__ import annotations

from typing import List


PATTERNS = {
    "crud": ["create", "read", "update", "delete"],
    "api": ["endpoint", "request", "response", "route"],
    "test": ["pytest", "assert", "fixture", "mock"],
    "refactor": ["rename", "extract", "cleanup", "simplify"],
    "bug": ["error", "exception", "traceback", "fix"],
}


def detect_patterns(query: str) -> List[str]:
    q = query.lower()
    found: List[str] = []
    for name, keywords in PATTERNS.items():
        if any(k in q for k in keywords):
            found.append(name)
    return found

