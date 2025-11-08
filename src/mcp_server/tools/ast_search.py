"""
MCP AST Search Tools

Provides AST-based semantic search tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.ast_search import get_ast_search_service
from src.search.ast_models import ASTSearchRequest, SymbolType, SearchScope
from src.indexing.ast_indexer import get_ast_indexer
from src.mcp_server.utils.param_parsing import parse_list_param

logger = logging.getLogger(__name__)


def register_ast_search_tools(mcp: FastMCP):
    """
    Register AST search tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def ast_semantic_search(
        query: str,
        limit: int = 10,
        symbol_types: Optional[Union[str, List[str]]] = None,
        languages: Optional[Union[str, List[str]]] = None,
        search_scope: str = "all",
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Advanced semantic search over code structure and symbols

        Performs semantic search over parsed AST metadata including functions,
        classes, imports, and their relationships. Provides rich filtering
        by symbol types, languages, and code structure.

        Args:
            query: Natural language search query (e.g., "async functions with error handling")
            limit: Maximum number of results to return (1-100, default: 10)
            symbol_types: Filter by symbol types (function, method, class, interface, etc.). Can be a JSON string or list.
            languages: Filter by programming languages (python, javascript, etc.). Can be a JSON string or list.
            search_scope: Search scope (all, symbols, classes, imports, default: all)
            min_score: Minimum similarity score (0.0-1.0, default: 0.0)

        Returns:
            Dict containing AST search results with detailed symbol information
        """
        logger.info(f"MCP AST search invoked: {query}")

        try:
            # Parse list parameters (handle both JSON strings and actual lists)
            symbol_types_list = parse_list_param(symbol_types)
            languages_list = parse_list_param(languages)

            # Convert string symbol types to enum
            symbol_type_enums = None
            if symbol_types_list:
                symbol_type_enums = []
                for st in symbol_types_list:
                    try:
                        symbol_type_enums.append(SymbolType(st.lower()))
                    except ValueError:
                        logger.warning(f"Invalid symbol type: {st}")

            # Convert search scope
            try:
                scope_enum = SearchScope(search_scope.lower())
            except ValueError:
                logger.warning(f"Invalid search scope: {search_scope}, using 'all'")
                scope_enum = SearchScope.ALL

            # Create search request
            request = ASTSearchRequest(
                query=query,
                limit=min(max(limit, 1), 100),
                symbol_types=symbol_type_enums,
                languages=languages_list,
                search_scope=scope_enum,
                min_score=max(0.0, min(min_score, 1.0)),
            )

            # Perform search
            search_service = get_ast_search_service()
            response = await search_service.search(request)

            # Convert to MCP response format
            results = []
            for result in response.results:
                result_dict = {
                    "file_path": result.file_path,
                    "file_name": result.file_name,
                    "language": result.language,
                    "similarity_score": round(result.similarity_score, 4),
                    "symbol_name": result.symbol_name,
                    "symbol_type": (
                        result.symbol_type.value if result.symbol_type else None
                    ),
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "signature": result.signature,
                    "docstring": result.docstring,
                    "parameters": result.parameters,
                    "return_type": result.return_type,
                    "decorators": result.decorators,
                    "base_classes": result.base_classes,
                    "interfaces": result.interfaces,
                    "visibility": result.visibility,
                    "is_static": result.is_static,
                    "is_abstract": result.is_abstract,
                    "is_async": result.is_async,
                    "metadata": result.metadata,
                }
                results.append(result_dict)

            return {
                "query": response.query,
                "results": results,
                "total_results": response.total_results,
                "search_time_ms": round(response.search_time_ms, 2),
                "symbols_found": response.symbols_found,
                "classes_found": response.classes_found,
                "imports_found": response.imports_found,
                "filters_applied": response.filters_applied,
                "languages_searched": response.languages_searched,
                "timestamp": response.timestamp,
            }

        except Exception as e:
            logger.error(f"AST search failed: {e}", exc_info=True)
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "search_time_ms": 0.0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def ast_search_classes(
        query: str,
        limit: int = 10,
        languages: Optional[Union[str, List[str]]] = None,
        is_abstract: Optional[bool] = None,
        has_inheritance: Optional[bool] = None,
        implements_interface: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Search for classes and interfaces with inheritance filtering

        Specialized search for classes and interfaces with filtering options
        for abstract classes, inheritance, and interface implementation.

        Args:
            query: Natural language search query
            limit: Maximum number of results (1-100, default: 10)
            languages: Filter by programming languages. Can be a JSON string or list.
            is_abstract: Filter abstract classes (true/false)
            has_inheritance: Filter classes with inheritance (true/false)
            implements_interface: Filter classes implementing interfaces (true/false)

        Returns:
            Dict containing class search results
        """
        logger.info(f"MCP class search invoked: {query}")

        try:
            # Parse list parameters (handle both JSON strings and actual lists)
            languages_list = parse_list_param(languages)

            # Create search request for classes only
            request = ASTSearchRequest(
                query=query,
                limit=min(max(limit, 1), 100),
                languages=languages_list,
                search_scope=SearchScope.CLASSES,
                is_abstract=is_abstract,
                has_inheritance=has_inheritance,
                implements_interface=implements_interface,
            )

            # Perform search
            search_service = get_ast_search_service()
            response = await search_service.search(request)

            # Convert to simplified class format
            classes = []
            for result in response.results:
                class_dict = {
                    "name": result.symbol_name,
                    "file_path": result.file_path,
                    "language": result.language,
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "docstring": result.docstring,
                    "base_classes": result.base_classes,
                    "interfaces": result.interfaces,
                    "is_abstract": result.is_abstract,
                    "is_interface": result.symbol_type == SymbolType.INTERFACE,
                    "visibility": result.visibility,
                    "decorators": result.decorators,
                    "methods": result.metadata.get("methods", []),
                    "fields": result.metadata.get("fields", []),
                    "similarity_score": round(result.similarity_score, 4),
                }
                classes.append(class_dict)

            return {
                "query": response.query,
                "classes": classes,
                "total_found": response.total_results,
                "search_time_ms": round(response.search_time_ms, 2),
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp,
            }

        except Exception as e:
            logger.error(f"Class search failed: {e}", exc_info=True)
            return {
                "query": query,
                "classes": [],
                "total_found": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def ast_index_directory(
        directory_path: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Index a directory for AST-based search

        Parses all supported code files in a directory and stores their
        AST metadata in the vector database for semantic search.

        Args:
            directory_path: Path to directory to index
            recursive: Whether to index subdirectories (default: true)

        Returns:
            Dict containing indexing results and statistics
        """
        logger.info(f"MCP AST indexing invoked: {directory_path}")

        try:
            from pathlib import Path
            import re

            # Resolve host -> container path if needed (Windows and Git Bash compatibility)
            def _resolve_dir(p: str) -> Path:
                # 1) Direct path as-is
                direct = Path(p)
                if direct.exists():
                    return direct

                # Normalize slashes
                p_norm = p.replace("\\", "/")

                # 2) Windows drive path like D:\\foo or D:/foo -> /d/foo
                m = re.match(r"^([A-Za-z]):/(.*)$", p_norm)
                if m:
                    drive = m.group(1).lower()
                    rest = m.group(2)
                    alt = Path(f"/{drive}/{rest}")
                    if alt.exists():
                        return alt

                # 3) Git Bash/Msys style /d/foo
                if re.match(r"^/[a-z]/", p_norm):
                    try3 = Path(p_norm)
                    if try3.exists():
                        return try3

                # 4) Optional JSON mappings via PATH_MAPPINGS_JSON
                mapping_str = os.environ.get("PATH_MAPPINGS_JSON")
                if mapping_str:
                    try:
                        import json
                        mappings = json.loads(mapping_str)
                        for host_prefix, container_prefix in mappings.items():
                            host_norm = host_prefix.replace("\\", "/")
                            if p_norm.lower().startswith(host_norm.lower()):
                                candidate = container_prefix.rstrip("/") + p_norm[len(host_norm):]
                                candidate_path = Path(candidate)
                                if candidate_path.exists():
                                    return candidate_path
                    except Exception as map_e:
                        logger.warning(f"Invalid PATH_MAPPINGS_JSON: {map_e}")

                return direct

            # Validate directory path (after resolution)
            dir_path = _resolve_dir(directory_path)
            if not dir_path.exists():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            if not dir_path.is_dir():
                return {
                    "error": f"Path is not a directory: {directory_path}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Perform indexing
            indexer = get_ast_indexer()
            result = await indexer.index_directory(dir_path, recursive=recursive)

            return {
                "success": True,
                "directory": result["directory"],
                "files_found": result["files_found"],
                "files_indexed": result["files_indexed"],
                "files_failed": result["files_failed"],
                "symbols_indexed": result["symbols_indexed"],
                "classes_indexed": result["classes_indexed"],
                "imports_indexed": result["imports_indexed"],
                "total_time_ms": round(result["total_time_ms"], 2),
                "recursive": result["recursive"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"AST indexing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def ast_search_stats() -> Dict[str, Any]:
        """
        Get AST search and indexing statistics

        Returns comprehensive statistics about AST indexing and search
        performance including number of indexed symbols, search performance,
        and error rates.

        Returns:
            Dict containing AST system statistics
        """
        logger.info("MCP AST stats requested")

        try:
            # Get search service stats
            search_service = get_ast_search_service()
            search_stats = search_service.get_stats()

            # Get indexer stats
            indexer = get_ast_indexer()
            indexer_stats = indexer.get_stats()

            # Get AST store stats
            from src.vector_db.ast_store import get_ast_vector_store

            ast_store = get_ast_vector_store()
            store_stats = ast_store.get_stats()

            return {
                "search_stats": search_stats,
                "indexing_stats": indexer_stats,
                "storage_stats": store_stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get AST stats: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def ast_search_functions(
        query: str,
        limit: int = 10,
        languages: Optional[Union[str, List[str]]] = None,
        is_async: Optional[bool] = None,
        has_parameters: Optional[bool] = None,
        has_return_type: Optional[bool] = None,
        visibility: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for functions and methods with advanced filtering

        Specialized search for functions and methods with detailed filtering
        options for async functions, parameters, return types, and visibility.

        Args:
            query: Natural language search query
            limit: Maximum number of results (1-100, default: 10)
            languages: Filter by programming languages. Can be a JSON string or list.
            is_async: Filter async functions (true/false)
            has_parameters: Filter functions with/without parameters (true/false)
            has_return_type: Filter functions with/without return types (true/false)
            visibility: Filter by visibility (public, private, protected)

        Returns:
            Dict containing function search results
        """
        logger.info(f"MCP function search invoked: {query}")

        try:
            # Parse list parameters (handle both JSON strings and actual lists)
            languages_list = parse_list_param(languages)

            # Create search request for functions only
            request = ASTSearchRequest(
                query=query,
                limit=min(max(limit, 1), 100),
                symbol_types=[SymbolType.FUNCTION, SymbolType.METHOD],
                languages=languages_list,
                search_scope=SearchScope.SYMBOLS,
                is_async=is_async,
                has_parameters=has_parameters,
                has_return_type=has_return_type,
                visibility=visibility,
            )

            # Perform search
            search_service = get_ast_search_service()
            response = await search_service.search(request)

            # Convert to simplified function format
            functions = []
            for result in response.results:
                function_dict = {
                    "name": result.symbol_name,
                    "file_path": result.file_path,
                    "language": result.language,
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "signature": result.signature,
                    "docstring": result.docstring,
                    "parameters": result.parameters,
                    "return_type": result.return_type,
                    "is_async": result.is_async,
                    "is_static": result.is_static,
                    "visibility": result.visibility,
                    "decorators": result.decorators,
                    "similarity_score": round(result.similarity_score, 4),
                }
                functions.append(function_dict)

            return {
                "query": response.query,
                "functions": functions,
                "total_found": response.total_results,
                "search_time_ms": round(response.search_time_ms, 2),
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp,
            }

        except Exception as e:
            logger.error(f"Function search failed: {e}", exc_info=True)
            return {
                "query": query,
                "functions": [],
                "total_found": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
