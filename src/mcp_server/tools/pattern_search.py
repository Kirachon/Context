"""
MCP Pattern Search Tools

Expose production-grade Tree-sitter pattern search via MCP.
"""

import sys
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.pattern_search import get_pattern_search_service

logger = logging.getLogger(__name__)


def register_pattern_search_tools(mcp: FastMCP):
    """Register pattern search tools with MCP server."""

    @mcp.tool()
    async def pattern_search_directory(
        directory_path: str,
        patterns: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        include_globs: Optional[List[str]] = None,
        exclude_globs: Optional[List[str]] = None,
        max_files: int = 500,
    ) -> Dict[str, Any]:
        """
        Search a directory for code patterns using Tree-sitter queries.

        Args:
            directory_path: Directory to scan
            patterns: Optional list of pattern names to apply (default: all)
            languages: Optional list of languages (default: all supported)
            include_globs: Optional include filters (e.g., ["src/**/*.py"])
            exclude_globs: Optional exclude filters (e.g., ["**/vendor/**"])
            max_files: Max files to scan (default: 500)
        """
        logger.info(
            f"MCP pattern_search_directory: {directory_path} patterns={patterns} languages={languages}"
        )
        try:
            root = Path(directory_path)
            if not root.exists() or not root.is_dir():
                return {
                    "error": f"Invalid directory: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            service = get_pattern_search_service()
            results = service.search_directory(
                root,
                patterns=patterns,
                languages=languages,
                include_globs=include_globs,
                exclude_globs=exclude_globs,
                max_files=max_files,
            )
            return {
                "directory": str(root),
                "total_matches": len(results),
                "results": [
                    {
                        "pattern": r.pattern_name,
                        "language": r.language,
                        "file_path": r.file_path,
                        "start_line": r.start_line,
                        "end_line": r.end_line,
                        "snippet": r.snippet,
                        "captures": r.captures,
                    }
                    for r in results
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"pattern_search_directory failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "results": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def pattern_search_code(
        language: str,
        code: str,
        patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run pattern search on a code snippet.
        """
        logger.info(
            f"MCP pattern_search_code: language={language}, patterns={patterns}"
        )
        try:
            service = get_pattern_search_service()
            results = service.search_code(language, code, patterns)
            return {
                "language": language,
                "total_matches": len(results),
                "results": [
                    {
                        "pattern": r.pattern_name,
                        "language": r.language,
                        "file_path": r.file_path,
                        "start_line": r.start_line,
                        "end_line": r.end_line,
                        "snippet": r.snippet,
                        "captures": r.captures,
                    }
                    for r in results
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"pattern_search_code failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "results": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
