"""
MCP Pattern Search Tools

Expose production-grade Tree-sitter pattern search via MCP.
"""

import sys
import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.pattern_search import get_pattern_search_service
from src.mcp_server.utils.param_parsing import parse_list_param

logger = logging.getLogger(__name__)


def register_pattern_search_tools(mcp: FastMCP):
    """Register pattern search tools with MCP server."""

    @mcp.tool()
    async def pattern_search_directory(
        directory_path: str,
        patterns: Optional[Union[str, List[str]]] = None,
        languages: Optional[Union[str, List[str]]] = None,
        include_globs: Optional[Union[str, List[str]]] = None,
        exclude_globs: Optional[Union[str, List[str]]] = None,
        max_files: int = 500,
    ) -> Dict[str, Any]:
        """
        Search a directory for code patterns using Tree-sitter queries.

        Args:
            directory_path: Directory to scan
            patterns: Optional list of pattern names to apply (default: all). Can be a JSON string or list.
            languages: Optional list of languages (default: all supported). Can be a JSON string or list.
            include_globs: Optional include filters (e.g., ["src/**/*.py"]). Can be a JSON string or list.
            exclude_globs: Optional exclude filters (e.g., ["**/vendor/**"]). Can be a JSON string or list.
            max_files: Max files to scan (default: 500)
        """
        # Parse list parameters (handle both JSON strings and actual lists)
        patterns_list = parse_list_param(patterns)
        languages_list = parse_list_param(languages)
        include_globs_list = parse_list_param(include_globs)
        exclude_globs_list = parse_list_param(exclude_globs)

        logger.info(
            f"MCP pattern_search_directory: {directory_path} patterns={patterns_list} languages={languages_list}"
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
                patterns=patterns_list,
                languages=languages_list,
                include_globs=include_globs_list,
                exclude_globs=exclude_globs_list,
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
        patterns: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Run pattern search on a code snippet.

        Args:
            language: Programming language of the code
            code: Code snippet to search
            patterns: Optional list of pattern names to apply. Can be a JSON string or list.
        """
        # Parse patterns parameter (handle both JSON strings and actual lists)
        patterns_list = parse_list_param(patterns)

        logger.info(
            f"MCP pattern_search_code: language={language}, patterns={patterns_list}"
        )
        try:
            service = get_pattern_search_service()
            results = service.search_code(language, code, patterns_list)
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
