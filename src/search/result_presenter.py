"""
Search Result Presentation & Navigation (Story 2-8)

Provides advanced result presentation, formatting, and navigation capabilities.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.search.models import SearchResult

logger = logging.getLogger(__name__)


class PresentationFormat(Enum):
    """Result presentation formats"""

    COMPACT = "compact"
    DETAILED = "detailed"
    SUMMARY = "summary"
    TREE = "tree"
    TIMELINE = "timeline"


class SortOrder(Enum):
    """Result sorting options"""

    RELEVANCE = "relevance"
    ALPHABETICAL = "alphabetical"
    DATE_MODIFIED = "date_modified"
    FILE_SIZE = "file_size"
    FILE_TYPE = "file_type"


@dataclass
class PresentationOptions:
    """Options for result presentation"""

    format: PresentationFormat = PresentationFormat.DETAILED
    sort_order: SortOrder = SortOrder.RELEVANCE
    group_by_file: bool = False
    group_by_type: bool = False
    show_context: bool = True
    show_line_numbers: bool = True
    highlight_matches: bool = True
    max_context_lines: int = 3
    truncate_long_lines: bool = True
    max_line_length: int = 120


@dataclass
class FormattedResult:
    """Formatted search result"""

    original_result: SearchResult
    formatted_content: str
    metadata: Dict[str, Any]
    navigation_info: Dict[str, Any]


class SearchResultPresenter:
    """
    Presents search results in various formats with navigation support

    Features:
    - Multiple presentation formats
    - Result grouping and sorting
    - Context highlighting
    - Navigation breadcrumbs
    - Interactive elements
    """

    def __init__(self):
        """Initialize result presenter"""
        self.default_options = PresentationOptions()

    def present_results(
        self, results: List[SearchResult], options: Optional[PresentationOptions] = None
    ) -> List[FormattedResult]:
        """
        Present search results with formatting

        Args:
            results: List of search results
            options: Presentation options

        Returns:
            List of formatted results
        """
        if not results:
            return []

        options = options or self.default_options

        # Sort results
        sorted_results = self._sort_results(results, options.sort_order)

        # Group results if requested
        if options.group_by_file or options.group_by_type:
            sorted_results = self._group_results(sorted_results, options)

        # Format each result
        formatted_results = []
        for result in sorted_results:
            formatted = self._format_result(result, options)
            formatted_results.append(formatted)

        return formatted_results

    def _sort_results(
        self, results: List[SearchResult], sort_order: SortOrder
    ) -> List[SearchResult]:
        """Sort results by specified order"""
        if sort_order == SortOrder.RELEVANCE:
            return sorted(results, key=lambda r: r.score, reverse=True)
        elif sort_order == SortOrder.ALPHABETICAL:
            return sorted(results, key=lambda r: r.file_path)
        elif sort_order == SortOrder.DATE_MODIFIED:
            return sorted(
                results, key=lambda r: r.metadata.get("modified_time", ""), reverse=True
            )
        elif sort_order == SortOrder.FILE_SIZE:
            return sorted(
                results, key=lambda r: r.metadata.get("file_size", 0), reverse=True
            )
        elif sort_order == SortOrder.FILE_TYPE:
            return sorted(results, key=lambda r: r.file_path.suffix)
        else:
            return results

    def _group_results(
        self, results: List[SearchResult], options: PresentationOptions
    ) -> List[SearchResult]:
        """Group results by file or type"""
        if options.group_by_file:
            # Group by file path
            file_groups = {}
            for result in results:
                file_path = str(result.file_path)
                if file_path not in file_groups:
                    file_groups[file_path] = []
                file_groups[file_path].append(result)

            # Flatten groups back to list
            grouped_results = []
            for file_path in sorted(file_groups.keys()):
                grouped_results.extend(file_groups[file_path])
            return grouped_results

        elif options.group_by_type:
            # Group by file type
            type_groups = {}
            for result in results:
                file_type = result.file_path.suffix or "no_extension"
                if file_type not in type_groups:
                    type_groups[file_type] = []
                type_groups[file_type].append(result)

            # Flatten groups back to list
            grouped_results = []
            for file_type in sorted(type_groups.keys()):
                grouped_results.extend(type_groups[file_type])
            return grouped_results

        return results

    def _format_result(
        self, result: SearchResult, options: PresentationOptions
    ) -> FormattedResult:
        """Format a single result"""
        if options.format == PresentationFormat.COMPACT:
            formatted_content = self._format_compact(result, options)
        elif options.format == PresentationFormat.DETAILED:
            formatted_content = self._format_detailed(result, options)
        elif options.format == PresentationFormat.SUMMARY:
            formatted_content = self._format_summary(result, options)
        elif options.format == PresentationFormat.TREE:
            formatted_content = self._format_tree(result, options)
        elif options.format == PresentationFormat.TIMELINE:
            formatted_content = self._format_timeline(result, options)
        else:
            formatted_content = self._format_detailed(result, options)

        # Generate metadata
        metadata = {
            "file_path": str(result.file_path),
            "score": result.score,
            "file_type": result.file_path.suffix,
            "line_count": len(result.content.split("\n")) if result.content else 0,
            "char_count": len(result.content) if result.content else 0,
        }

        # Generate navigation info
        navigation_info = {
            "breadcrumb": self._generate_breadcrumb(result.file_path),
            "line_number": getattr(result, "line_number", None),
            "column_number": getattr(result, "column_number", None),
        }

        return FormattedResult(
            original_result=result,
            formatted_content=formatted_content,
            metadata=metadata,
            navigation_info=navigation_info,
        )

    def _format_compact(
        self, result: SearchResult, options: PresentationOptions
    ) -> str:
        """Format result in compact mode"""
        file_path = str(result.file_path)
        score = f"{result.score:.3f}"

        content_preview = ""
        if result.content and options.show_context:
            lines = result.content.split("\n")[:1]  # First line only
            content_preview = lines[0][:50] + "..." if len(lines[0]) > 50 else lines[0]

        return f"[{score}] {file_path}: {content_preview}"

    def _format_detailed(
        self, result: SearchResult, options: PresentationOptions
    ) -> str:
        """Format result in detailed mode"""
        lines = []

        # Header
        file_path = str(result.file_path)
        score = f"{result.score:.3f}"
        lines.append(f"📄 {file_path} (score: {score})")

        # Metadata
        if result.metadata:
            size = result.metadata.get("file_size", "unknown")
            modified = result.metadata.get("modified_time", "unknown")
            lines.append(f"   Size: {size} | Modified: {modified}")

        # Content with context
        if result.content and options.show_context:
            lines.append("   Content:")
            content_lines = result.content.split("\n")
            for i, line in enumerate(content_lines[: options.max_context_lines]):
                line_num = f"{i+1:3d}" if options.show_line_numbers else ""
                formatted_line = line
                if options.truncate_long_lines and len(line) > options.max_line_length:
                    formatted_line = line[: options.max_line_length] + "..."
                lines.append(f"   {line_num} | {formatted_line}")

        return "\n".join(lines)

    def _format_summary(
        self, result: SearchResult, options: PresentationOptions
    ) -> str:
        """Format result in summary mode"""
        file_path = str(result.file_path)
        file_type = result.file_path.suffix or "unknown"
        score = f"{result.score:.3f}"

        return f"{file_path} ({file_type}) - Score: {score}"

    def _format_tree(self, result: SearchResult, options: PresentationOptions) -> str:
        """Format result in tree mode"""
        parts = result.file_path.parts
        tree_lines = []

        for i, part in enumerate(parts):
            indent = "  " * i
            if i == len(parts) - 1:
                # File (leaf)
                score = f"{result.score:.3f}"
                tree_lines.append(f"{indent}📄 {part} ({score})")
            else:
                # Directory
                tree_lines.append(f"{indent}📁 {part}/")

        return "\n".join(tree_lines)

    def _format_timeline(
        self, result: SearchResult, options: PresentationOptions
    ) -> str:
        """Format result in timeline mode"""
        file_path = str(result.file_path)
        modified_time = result.metadata.get("modified_time", "unknown")
        score = f"{result.score:.3f}"

        return f"[{modified_time}] {file_path} (score: {score})"

    def _generate_breadcrumb(self, file_path) -> List[str]:
        """Generate breadcrumb navigation"""
        return list(file_path.parts)


# Global presenter instance
_result_presenter: Optional[SearchResultPresenter] = None


def get_result_presenter() -> SearchResultPresenter:
    """Get global result presenter instance"""
    global _result_presenter
    if _result_presenter is None:
        _result_presenter = SearchResultPresenter()
    return _result_presenter
