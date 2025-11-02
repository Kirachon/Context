"""
Search Result Navigation (Story 2-8)

Provides navigation capabilities for search results including filtering,
jumping, and result exploration.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from src.search.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class NavigationFilter:
    """Filter for result navigation"""

    file_types: Optional[List[str]] = None
    directories: Optional[List[str]] = None
    score_threshold: Optional[float] = None
    content_pattern: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None


class SearchResultNavigator:
    """
    Provides navigation capabilities for search results

    Features:
    - Result filtering and refinement
    - Jump to specific results
    - Result exploration
    - Context expansion
    - Related result discovery
    """

    def __init__(self):
        """Initialize result navigator"""
        self.current_results: List[SearchResult] = []
        self.current_index: int = 0
        self.navigation_history: List[int] = []

    def set_results(self, results: List[SearchResult]):
        """Set current result set"""
        self.current_results = results
        self.current_index = 0
        self.navigation_history = []

    def filter_results(
        self, results: List[SearchResult], filter_options: NavigationFilter
    ) -> List[SearchResult]:
        """Filter results based on navigation filter"""
        filtered = results

        # Filter by file types
        if filter_options.file_types:
            filtered = [
                r
                for r in filtered
                if r.file_path.suffix.lower()
                in [
                    f.lower() if f.startswith(".") else f".{f.lower()}"
                    for f in filter_options.file_types
                ]
            ]

        # Filter by directories
        if filter_options.directories:
            filtered = [
                r
                for r in filtered
                if any(
                    str(r.file_path).startswith(d) for d in filter_options.directories
                )
            ]

        # Filter by score threshold
        if filter_options.score_threshold is not None:
            filtered = [
                r for r in filtered if r.score >= filter_options.score_threshold
            ]

        # Filter by content pattern
        if filter_options.content_pattern:
            pattern = filter_options.content_pattern.lower()
            filtered = [
                r for r in filtered if r.content and pattern in r.content.lower()
            ]

        # Exclude patterns
        if filter_options.exclude_patterns:
            for pattern in filter_options.exclude_patterns:
                filtered = [
                    r
                    for r in filtered
                    if not (r.content and pattern.lower() in r.content.lower())
                ]

        return filtered

    def jump_to_result(self, index: int) -> Optional[SearchResult]:
        """Jump to specific result by index"""
        if 0 <= index < len(self.current_results):
            self.navigation_history.append(self.current_index)
            self.current_index = index
            return self.current_results[index]
        return None

    def next_result(self) -> Optional[SearchResult]:
        """Navigate to next result"""
        if self.current_index < len(self.current_results) - 1:
            return self.jump_to_result(self.current_index + 1)
        return None

    def previous_result(self) -> Optional[SearchResult]:
        """Navigate to previous result"""
        if self.current_index > 0:
            return self.jump_to_result(self.current_index - 1)
        return None

    def go_back(self) -> Optional[SearchResult]:
        """Go back to previous navigation position"""
        if self.navigation_history:
            previous_index = self.navigation_history.pop()
            self.current_index = previous_index
            return self.current_results[previous_index]
        return None

    def get_current_result(self) -> Optional[SearchResult]:
        """Get current result"""
        if 0 <= self.current_index < len(self.current_results):
            return self.current_results[self.current_index]
        return None

    def find_related_results(
        self, result: SearchResult, max_results: int = 5
    ) -> List[SearchResult]:
        """Find results related to the given result"""
        related = []

        # Same file results
        same_file = [
            r
            for r in self.current_results
            if r.file_path == result.file_path and r != result
        ]
        related.extend(same_file[: max_results // 2])

        # Same directory results
        same_dir = [
            r
            for r in self.current_results
            if r.file_path.parent == result.file_path.parent
            and r != result
            and r not in related
        ]
        related.extend(same_dir[: max_results // 2])

        # Similar score results
        score_range = 0.1
        similar_score = [
            r
            for r in self.current_results
            if abs(r.score - result.score) <= score_range
            and r != result
            and r not in related
        ]
        related.extend(similar_score[: max_results - len(related)])

        return related[:max_results]

    def expand_context(
        self, result: SearchResult, lines_before: int = 5, lines_after: int = 5
    ) -> Optional[str]:
        """Expand context around a result"""
        try:
            file_path = Path(result.file_path)
            if not file_path.exists():
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            # Find the line number (if available)
            line_number = getattr(result, "line_number", None)
            if line_number is None:
                # Try to find the content in the file
                if result.content:
                    for i, line in enumerate(all_lines):
                        if result.content.strip() in line.strip():
                            line_number = i + 1
                            break

            if line_number is None:
                return result.content

            # Extract context
            start_line = max(0, line_number - lines_before - 1)
            end_line = min(len(all_lines), line_number + lines_after)

            context_lines = []
            for i in range(start_line, end_line):
                line_num = i + 1
                marker = ">>>" if line_num == line_number else "   "
                context_lines.append(f"{marker} {line_num:3d}: {all_lines[i].rstrip()}")

            return "\n".join(context_lines)

        except Exception as e:
            logger.warning(f"Failed to expand context for {result.file_path}: {e}")
            return result.content

    def get_navigation_summary(self) -> Dict[str, Any]:
        """Get navigation summary"""
        return {
            "total_results": len(self.current_results),
            "current_index": self.current_index,
            "current_result": (
                str(self.current_results[self.current_index].file_path)
                if self.current_results
                else None
            ),
            "has_previous": self.current_index > 0,
            "has_next": self.current_index < len(self.current_results) - 1,
            "history_depth": len(self.navigation_history),
        }

    def create_result_index(self) -> Dict[str, List[int]]:
        """Create index of results by various criteria"""
        index = {"by_file_type": {}, "by_directory": {}, "by_score_range": {}}

        for i, result in enumerate(self.current_results):
            # Index by file type
            file_type = result.file_path.suffix or "no_extension"
            if file_type not in index["by_file_type"]:
                index["by_file_type"][file_type] = []
            index["by_file_type"][file_type].append(i)

            # Index by directory
            directory = str(result.file_path.parent)
            if directory not in index["by_directory"]:
                index["by_directory"][directory] = []
            index["by_directory"][directory].append(i)

            # Index by score range
            score_range = f"{int(result.score * 10) / 10:.1f}-{int(result.score * 10) / 10 + 0.1:.1f}"
            if score_range not in index["by_score_range"]:
                index["by_score_range"][score_range] = []
            index["by_score_range"][score_range].append(i)

        return index


# Global navigator instance
_result_navigator: Optional[SearchResultNavigator] = None


def get_result_navigator() -> SearchResultNavigator:
    """Get global result navigator instance"""
    global _result_navigator
    if _result_navigator is None:
        _result_navigator = SearchResultNavigator()
    return _result_navigator


# Module-level stub function for MCP tool integration
def navigate_results(results: list, current: int, direction: str) -> Dict:
    """
    Navigate through search results.

    Stub implementation for MCP tool integration.

    Args:
        results: List of search results
        current: Current result index
        direction: Navigation direction ('next', 'prev', 'first', 'last')

    Returns:
        Dict with status and navigation info
    """
    logger.warning(f"SearchResultNavigator stub called with {len(results)} results, current={current}, direction={direction}")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "navigate_results is a stub implementation",
        "results": [],
        "current_index": current,
        "direction": direction,
        "data": {}
    }
