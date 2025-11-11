from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

try:  # Optional dependency
    from rich.console import Console  # type: ignore
    from rich.panel import Panel  # type: ignore
except Exception:  # pragma: no cover - fallback path exercised in tests
    Console = None  # type: ignore
    Panel = None  # type: ignore

from src.search.query_refiner import QueryRefiner


@dataclass
class EnhancementResult:
    original: str
    enhanced: str
    suggestions: List[str]
    used_rich: bool

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "enhanced": self.enhanced,
            "suggestions": list(self.suggestions),
            "used_rich": self.used_rich,
        }


class InteractivePromptEnhancer:
    """Interactive prompt enhancer with graceful fallback.

    - Uses Rich for a nicer TUI when available
    - Falls back to plain output without requiring extra dependencies
    - Stateless core; relies on QueryRefiner for suggestions
    """

    def __init__(self) -> None:
        self._refiner = QueryRefiner()
        self._console = Console() if Console is not None else None

    @property
    def has_rich(self) -> bool:
        return self._console is not None

    def enhance_once(self, text: str) -> EnhancementResult:
        suggestions = self._refiner.suggest_refinements(text)
        # Keep enhanced text identical for safety; present suggestions to the user
        enhanced = text
        # No console output here; interactive UI should be handled by a front-end caller.
        return EnhancementResult(
            original=text,
            enhanced=enhanced,
            suggestions=suggestions,
            used_rich=self.has_rich,
        )

