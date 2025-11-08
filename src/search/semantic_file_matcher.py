from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


def _tokenize(s: str) -> List[str]:
    # Split on non-alphanumerics including underscore to catch names like user_service
    return [t for t in re.split(r"[^a-zA-Z0-9]+", s.lower()) if len(t) >= 3]


@dataclass
class FileMatch:
    path: str
    score: float

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["path"] = str(self.path)
        d["score"] = float(self.score)
        return d


class SemanticFileMatcher:
    """Lightweight file matcher based on lexical similarity of query to paths.

    Safe-by-default: no external dependencies, scans only small trees by default.
    """

    def __init__(self, root: str = ".", max_files: int = 3000):
        self.root = root
        self.max_files = max_files

    def match(self, query: str, limit: int = 10, include_extensions: Optional[List[str]] = None) -> List[FileMatch]:
        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return []

        matches: List[FileMatch] = []
        total = 0
        for dirpath, _, filenames in os.walk(self.root):
            if any(skip in dirpath for skip in (".git", "node_modules", "__pycache__", ".venv", ".pytest_cache")):
                continue
            for fn in filenames:
                if include_extensions and not any(fn.endswith(ext) for ext in include_extensions):
                    continue
                path = os.path.join(dirpath, fn)
                tokens = set(_tokenize(fn + " " + dirpath.replace(os.sep, " ")))
                if not tokens:
                    continue
                overlap = q_tokens.intersection(tokens)
                if overlap:
                    # Jaccard-like score weighted towards query coverage
                    score = min(1.0, len(overlap) / max(1, len(q_tokens)))
                    matches.append(FileMatch(path=path, score=score))
                total += 1
                if total >= self.max_files:
                    break
            if total >= self.max_files:
                break

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[: max(1, min(limit, 50))]

