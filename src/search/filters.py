"""
Search Filters

Filtering logic for search results.
"""

import os
import logging
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from src.search.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Search filters configuration"""

    file_types: Optional[List[str]] = None
    directories: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    min_score: float = 0.0
    # Advanced filters (Story 2.4)
    authors: Optional[List[str]] = None
    modified_after: Optional[str] = None  # ISO-8601
    modified_before: Optional[str] = None  # ISO-8601


def apply_filters(
    results: List[SearchResult], filters: SearchFilters
) -> List[SearchResult]:
    """
    Apply filters to search results

    Args:
        results: List of search results
        filters: Filters to apply

    Returns:
        Filtered search results
    """
    if not results:
        return results

    filtered_results = results.copy()

    # Apply file type filter
    if filters.file_types:
        filtered_results = _filter_by_file_types(filtered_results, filters.file_types)
        logger.debug(f"After file type filter: {len(filtered_results)} results")

    # Apply directory filter
    if filters.directories:
        filtered_results = _filter_by_directories(filtered_results, filters.directories)
        logger.debug(f"After directory filter: {len(filtered_results)} results")

    # Apply exclude patterns filter
    if filters.exclude_patterns:
        filtered_results = _filter_by_exclude_patterns(
            filtered_results, filters.exclude_patterns
        )
        logger.debug(f"After exclude patterns filter: {len(filtered_results)} results")

    # Apply author filter (only if metadata has authors)
    if getattr(filters, "authors", None):
        filtered_results = _filter_by_authors(filtered_results, filters.authors)
        logger.debug(f"After authors filter: {len(filtered_results)} results")

    # Apply modified date filters
    if getattr(filters, "modified_after", None) or getattr(
        filters, "modified_before", None
    ):
        filtered_results = _filter_by_modified_date(
            filtered_results, filters.modified_after, filters.modified_before
        )
        logger.debug(f"After modified date filter: {len(filtered_results)} results")

    # Apply minimum score filter
    if filters.min_score > 0.0:
        filtered_results = _filter_by_min_score(filtered_results, filters.min_score)
        logger.debug(f"After min score filter: {len(filtered_results)} results")

    logger.info(f"Applied filters: {len(results)} → {len(filtered_results)} results")
    return filtered_results


def _filter_by_file_types(
    results: List[SearchResult], file_types: List[str]
) -> List[SearchResult]:
    """Filter results by file types/extensions"""
    # Normalize file types (ensure they start with .)
    normalized_types = []
    for file_type in file_types:
        if not file_type.startswith("."):
            file_type = "." + file_type
        normalized_types.append(file_type.lower())

    filtered = []
    for result in results:
        file_ext = os.path.splitext(result.file_path)[1].lower()
        if file_ext in normalized_types:
            filtered.append(result)

    return filtered


def _filter_by_directories(
    results: List[SearchResult], directories: List[str]
) -> List[SearchResult]:
    """Filter results by directory paths"""
    # Normalize directory paths
    normalized_dirs = []
    for directory in directories:
        # Remove leading/trailing slashes and normalize
        normalized_dir = directory.strip("/\\").replace("\\", "/")
        normalized_dirs.append(normalized_dir.lower())

    filtered = []
    for result in results:
        # Normalize result path
        result_path = result.file_path.replace("\\", "/").lower()

        # Check if any directory matches
        for directory in normalized_dirs:
            if directory in result_path:
                filtered.append(result)
                break

    return filtered


def _filter_by_exclude_patterns(
    results: List[SearchResult], exclude_patterns: List[str]
) -> List[SearchResult]:
    """Filter out results matching exclude patterns"""
    # Normalize exclude patterns
    normalized_patterns = [pattern.lower() for pattern in exclude_patterns]

    filtered = []
    for result in results:
        # Normalize result path
        result_path = result.file_path.replace("\\", "/").lower()

        # Check if any exclude pattern matches
        should_exclude = any(pattern in result_path for pattern in normalized_patterns)
        if not should_exclude:
            filtered.append(result)

    return filtered


def _filter_by_authors(
    results: List[SearchResult], authors: List[str]
) -> List[SearchResult]:
    """Filter results by author name(s) using metadata['author'] if available."""
    if not authors:
        return results
    normalized = {
        a.strip().lower() for a in authors if isinstance(a, str) and a.strip()
    }
    filtered = []
    for result in results:
        author = (result.metadata or {}).get("author")
        if isinstance(author, str) and author.strip().lower() in normalized:
            filtered.append(result)
    return filtered


def _filter_by_modified_date(
    results: List[SearchResult],
    modified_after: Optional[str],
    modified_before: Optional[str],
) -> List[SearchResult]:
    """Filter results by modification date using metadata['modified_time'] or fallback to 'indexed_time'."""
    if not results:
        return results

    start_dt = None
    end_dt = None
    try:
        if modified_after:
            start_dt = datetime.fromisoformat(modified_after.replace("Z", "+00:00"))
    except Exception:
        start_dt = None
    try:
        if modified_before:
            end_dt = datetime.fromisoformat(modified_before.replace("Z", "+00:00"))
    except Exception:
        end_dt = None

    if not start_dt and not end_dt:
        return results

    filtered = []
    for result in results:
        ts_str = (result.metadata or {}).get("modified_time") or (
            result.metadata or {}
        ).get("indexed_time")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            continue
        if start_dt and ts < start_dt:
            continue
        if end_dt and ts > end_dt:
            continue
        filtered.append(result)
    return filtered


def _filter_by_min_score(
    results: List[SearchResult], min_score: float
) -> List[SearchResult]:
    """Filter results by minimum similarity score"""
    filtered = []
    for result in results:
        if result.similarity_score >= min_score:
            filtered.append(result)

    return filtered


def validate_filters(filters: SearchFilters) -> List[str]:
    """
    Validate search filters

    Args:
        filters: Filters to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validate file types
    if filters.file_types:
        for file_type in filters.file_types:
            if not isinstance(file_type, str) or len(file_type.strip()) == 0:
                errors.append(f"Invalid file type: {file_type}")

    # Validate directories
    if filters.directories:
        for directory in filters.directories:
            if not isinstance(directory, str) or len(directory.strip()) == 0:
                errors.append(f"Invalid directory: {directory}")

    # Validate exclude patterns
    if filters.exclude_patterns:
        for pattern in filters.exclude_patterns:
            if not isinstance(pattern, str) or len(pattern.strip()) == 0:
                errors.append(f"Invalid exclude pattern: {pattern}")

    # Validate min score
    if not (0.0 <= filters.min_score <= 1.0):
        errors.append(
            f"Min score must be between 0.0 and 1.0, got: {filters.min_score}"
        )

    # Validate authors
    if getattr(filters, "authors", None):
        for author in filters.authors:
            if not isinstance(author, str) or len(author.strip()) == 0:
                errors.append(f"Invalid author: {author}")

    # Validate modified date range
    for label, dt_str in [
        ("modified_after", getattr(filters, "modified_after", None)),
        ("modified_before", getattr(filters, "modified_before", None)),
    ]:
        if dt_str:
            try:
                datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                errors.append(f"Invalid {label} datetime (expected ISO 8601): {dt_str}")

    return errors


def get_supported_file_types() -> List[str]:
    """
    Get list of supported file types

    Returns:
        List of supported file extensions
    """
    return [".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".hpp", ".h", ".cc"]


def get_common_exclude_patterns() -> List[str]:
    """
    Get list of common exclude patterns

    Returns:
        List of common patterns to exclude
    """
    return [
        "node_modules",
        "__pycache__",
        ".git",
        ".vscode",
        ".idea",
        "build",
        "dist",
        "target",
        "bin",
        "obj",
        "test",
        "tests",
        "spec",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
    ]
