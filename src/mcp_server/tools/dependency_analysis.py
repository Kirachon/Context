"""
MCP Dependency Analysis Tools (Story 2.5)

Provides dependency graph, cycle detection, impact analysis, and reference lookup
via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.analysis.dependency_analysis import DependencyAnalyzer
from src.parsing.parser import get_parser
from src.parsing.models import Language

logger = logging.getLogger(__name__)


def register_dependency_tools(mcp: FastMCP):
    """
    Register dependency analysis tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def dependency_graph(
        directory_path: str,
        recursive: bool = True,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        Build and return dependency graph for a codebase

        Analyzes imports, inheritance, and interfaces to construct a file-level
        dependency graph with adjacency lists.

        Args:
            directory_path: Path to directory to analyze
            recursive: Whether to analyze subdirectories (default: true)
            max_files: Maximum files to analyze (default: 100)

        Returns:
            Dict with adjacency lists (outgoing and incoming edges)
        """
        logger.info(f"MCP dependency graph invoked: {directory_path}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Parse files
            parser = get_parser()
            parse_results = []

            pattern = "**/*" if recursive else "*"
            for ext in [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]:
                for file_path in dir_path.glob(f"{pattern}{ext}"):
                    if len(parse_results) >= max_files:
                        break
                    try:
                        result = parser.parse(file_path)
                        if result.parse_success:
                            parse_results.append(result)
                    except Exception as e:
                        logger.debug(f"Failed to parse {file_path}: {e}")

            if not parse_results:
                return {
                    "error": "No files could be parsed successfully",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Build dependency graph
            analyzer = DependencyAnalyzer(parse_results)
            adj_out, adj_in = analyzer.build_graph()

            # Convert sets to lists for JSON serialization
            return {
                "success": True,
                "files_analyzed": len(parse_results),
                "adjacency_out": {k: sorted(list(v)) for k, v in adj_out.items()},
                "adjacency_in": {k: sorted(list(v)) for k, v in adj_in.items()},
                "total_edges": sum(len(v) for v in adj_out.values()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Dependency graph analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    @mcp.tool()
    async def dependency_cycles(
        directory_path: str,
        recursive: bool = True,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        Detect circular dependencies in a codebase

        Uses depth-first search to identify cycles in the file-level dependency
        graph. Returns all detected cycles.

        Args:
            directory_path: Path to directory to analyze
            recursive: Whether to analyze subdirectories (default: true)
            max_files: Maximum files to analyze (default: 100)

        Returns:
            Dict with list of detected cycles
        """
        logger.info(f"MCP cycle detection invoked: {directory_path}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Parse files
            parser = get_parser()
            parse_results = []

            pattern = "**/*" if recursive else "*"
            for ext in [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]:
                for file_path in dir_path.glob(f"{pattern}{ext}"):
                    if len(parse_results) >= max_files:
                        break
                    try:
                        result = parser.parse(file_path)
                        if result.parse_success:
                            parse_results.append(result)
                    except Exception as e:
                        logger.debug(f"Failed to parse {file_path}: {e}")

            if not parse_results:
                return {
                    "error": "No files could be parsed successfully",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Detect cycles
            analyzer = DependencyAnalyzer(parse_results)
            cycles = analyzer.detect_cycles()

            return {
                "success": True,
                "files_analyzed": len(parse_results),
                "cycles_detected": len(cycles),
                "cycles": [list(c) for c in cycles],
                "has_circular_dependencies": len(cycles) > 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Cycle detection failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    @mcp.tool()
    async def dependency_impact(
        directory_path: str,
        file_path: str,
        recursive: bool = True,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze impact of changes to a specific file

        Computes transitive dependents: all files that would be affected if the
        specified file changes.

        Args:
            directory_path: Path to directory to analyze
            file_path: Relative path of file to analyze impact for
            recursive: Whether to analyze subdirectories (default: true)
            max_files: Maximum files to analyze (default: 100)

        Returns:
            Dict with list of impacted files
        """
        logger.info(f"MCP impact analysis invoked: {directory_path}, file: {file_path}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Parse files
            parser = get_parser()
            parse_results = []

            pattern = "**/*" if recursive else "*"
            for ext in [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]:
                for fp in dir_path.glob(f"{pattern}{ext}"):
                    if len(parse_results) >= max_files:
                        break
                    try:
                        result = parser.parse(fp)
                        if result.parse_success:
                            parse_results.append(result)
                    except Exception as e:
                        logger.debug(f"Failed to parse {fp}: {e}")

            if not parse_results:
                return {
                    "error": "No files could be parsed successfully",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Compute impact
            analyzer = DependencyAnalyzer(parse_results)
            impacted = analyzer.impact_of_change(file_path)

            return {
                "success": True,
                "files_analyzed": len(parse_results),
                "target_file": file_path,
                "impacted_files": sorted(list(impacted)),
                "impact_count": len(impacted),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Impact analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    @mcp.tool()
    async def dependency_references(
        directory_path: str,
        symbol_name: str,
        recursive: bool = True,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        Find references to a symbol across the codebase

        Locates all files and locations where a given symbol (function, class, etc.)
        is referenced or used.

        Args:
            directory_path: Path to directory to analyze
            symbol_name: Name of symbol to find references for
            recursive: Whether to analyze subdirectories (default: true)
            max_files: Maximum files to analyze (default: 100)

        Returns:
            Dict with list of reference locations
        """
        logger.info(f"MCP reference lookup invoked: {directory_path}, symbol: {symbol_name}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Parse files
            parser = get_parser()
            parse_results = []

            pattern = "**/*" if recursive else "*"
            for ext in [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]:
                for fp in dir_path.glob(f"{pattern}{ext}"):
                    if len(parse_results) >= max_files:
                        break
                    try:
                        result = parser.parse(fp)
                        if result.parse_success:
                            parse_results.append(result)
                    except Exception as e:
                        logger.debug(f"Failed to parse {fp}: {e}")

            if not parse_results:
                return {
                    "error": "No files could be parsed successfully",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Find references
            analyzer = DependencyAnalyzer(parse_results)
            references = analyzer.find_references(symbol_name)

            # Format references for response
            ref_list = []
            for ref in references:
                ref_list.append({
                    "source_file": ref.source_file,
                    "target_file": ref.target_file,
                    "source_symbol": ref.source_symbol,
                    "target_symbol": ref.target_symbol,
                    "relation": ref.relation
                })

            return {
                "success": True,
                "files_analyzed": len(parse_results),
                "symbol": symbol_name,
                "references_found": len(ref_list),
                "references": ref_list,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Reference lookup failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

