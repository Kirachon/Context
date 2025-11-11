"""
MCP Search Tools

Provides semantic search operations via MCP protocol.
"""

import sys
import os
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.semantic_search import search_code, get_search_stats
from src.search.models import SearchRequest
from src.search.filters import get_supported_file_types, get_common_exclude_patterns
from src.mcp_server.utils.param_parsing import parse_list_param

logger = logging.getLogger(__name__)


def register_search_tools(mcp: FastMCP):
    """
    Register search tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def semantic_search(
        query: str,
        limit: int = 10,
        file_types: Optional[Union[str, List[str]]] = None,
        min_score: float = 0.0,
        project_id: Optional[str] = None,
        scope: str = "workspace",
    ) -> Dict[str, Any]:
        """
        Search codebase using natural language query

        Performs semantic search over indexed code files using vector embeddings.
        Returns relevant code files ranked by similarity.

        In workspace mode, supports multi-project search with different scope options.
        In single-project mode, ignores project_id and scope parameters.

        Args:
            query: Natural language search query (e.g., "authentication functions")
            limit: Maximum number of results to return (1-100, default: 10)
            file_types: Filter by file extensions (e.g., [".py", ".js"]). Can be a JSON string or list.
            min_score: Minimum similarity score (0.0-1.0, default: 0.0)
            project_id: Target project ID (workspace mode only, required for project/dependencies/related scopes)
            scope: Search scope - "project", "dependencies", "workspace", "related" (workspace mode only, default: "workspace")

        Returns:
            Dict containing search results with file paths, scores, and snippets
        """
        logger.info(f"MCP tool invoked: semantic_search with query: {query}, scope: {scope}, project: {project_id}")

        try:
            # Check if we're in workspace mode
            from src.mcp_server.http_server import is_workspace_mode, get_workspace_manager

            if is_workspace_mode():
                # Workspace-aware search
                workspace_manager = get_workspace_manager()

                # Import workspace search components
                from src.search.workspace_search import SearchScope, get_workspace_search

                # Initialize workspace search if needed
                workspace_search = get_workspace_search()
                if not workspace_search.workspace_manager:
                    from src.search.workspace_search import initialize_workspace_search
                    initialize_workspace_search(
                        workspace_manager=workspace_manager,
                        vector_store=None,
                        relationship_graph=workspace_manager.relationship_graph
                    )
                    workspace_search = get_workspace_search()

                # Convert scope string to enum
                try:
                    search_scope = SearchScope(scope.lower())
                except ValueError:
                    logger.warning(f"Invalid scope '{scope}', defaulting to WORKSPACE")
                    search_scope = SearchScope.WORKSPACE

                # Parse file types for filters
                file_types_list = parse_list_param(file_types)
                filters = None
                if file_types_list or min_score > 0.0:
                    from src.search.filters import SearchFilters
                    filters = SearchFilters(
                        file_types=file_types_list,
                        min_score=min_score
                    )

                # Perform workspace search
                start_time = time.time()
                enhanced_results, metrics = await workspace_search.search(
                    query=query,
                    scope=search_scope,
                    project_id=project_id,
                    limit=limit,
                    filters=filters
                )
                search_time_ms = (time.time() - start_time) * 1000

                # Format results
                formatted_results = []
                for result in enhanced_results:
                    formatted_result = {
                        "file_path": result.file_path,
                        "file_name": result.file_name,
                        "file_type": result.file_type,
                        "similarity_score": round(result.similarity_score, 3),
                        "confidence_score": round(result.confidence_score, 3),
                        "file_size": result.file_size,
                        "snippet": (
                            result.snippet[:200] + "..."
                            if result.snippet and len(result.snippet) > 200
                            else result.snippet
                        ),
                        "project_id": result.project_id,
                        "project_name": result.project_name,
                        "relationship_context": result.relationship_context,
                    }
                    formatted_results.append(formatted_result)

                result = {
                    "query": query,
                    "mode": "workspace",
                    "scope": scope,
                    "target_project": project_id,
                    "total_results": len(enhanced_results),
                    "returned_results": len(formatted_results),
                    "search_time_ms": round(search_time_ms, 2),
                    "results": formatted_results,
                    "metrics": {
                        "projects_searched": metrics.projects_searched,
                        "projects_searched_list": metrics.projects_searched_list,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                logger.info(
                    f"Workspace search completed: {len(enhanced_results)} results in {search_time_ms:.2f}ms "
                    f"(searched {metrics.projects_searched} projects)"
                )
                return result

            else:
                # Single-project mode (existing implementation)
                # Parse list parameters (handle both JSON strings and actual lists)
                file_types_list = parse_list_param(file_types)

                # Create search request
                request = SearchRequest(
                    query=query, limit=limit, file_types=file_types_list, min_score=min_score
                )

                # Perform search
                response = await search_code(request)

                # Format results for MCP
                formatted_results = []
                for result in response.results:
                    formatted_result = {
                        "file_path": result.file_path,
                        "file_name": result.file_name,
                        "file_type": result.file_type,
                        "similarity_score": round(result.similarity_score, 3),
                        "confidence_score": round(result.confidence_score, 3),
                        "file_size": result.file_size,
                        "snippet": (
                            result.snippet[:200] + "..."
                            if result.snippet and len(result.snippet) > 200
                            else result.snippet
                        ),
                    }
                    formatted_results.append(formatted_result)

                result = {
                    "query": response.query,
                    "mode": "single-project",
                    "total_results": response.total_results,
                    "returned_results": len(formatted_results),
                    "search_time_ms": round(response.search_time_ms, 2),
                    "results": formatted_results,
                    "filters_applied": response.filters_applied,
                    "timestamp": response.timestamp,
                }

                logger.info(
                    f"Semantic search completed: {response.total_results} results in {response.search_time_ms:.2f}ms"
                )
                return result

        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def search_with_filters(
        query: str,
        limit: int = 10,
        file_types: Optional[Union[str, List[str]]] = None,
        directories: Optional[Union[str, List[str]]] = None,
        exclude_patterns: Optional[Union[str, List[str]]] = None,
        min_score: float = 0.0,
        authors: Optional[Union[str, List[str]]] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search codebase with advanced filtering options

        Performs semantic search with comprehensive filtering by file type,
        directory, and exclude patterns.

        Args:
            query: Natural language search query
            limit: Maximum number of results (1-100, default: 10)
            file_types: Filter by file extensions (e.g., [".py", ".js"]). Can be a JSON string or list.
            directories: Filter by directory paths (e.g., ["src", "lib"]). Can be a JSON string or list.
            exclude_patterns: Exclude patterns (e.g., ["test", "__pycache__"]). Can be a JSON string or list.
            min_score: Minimum similarity score (0.0-1.0, default: 0.0)
            authors: Filter by authors. Can be a JSON string or list.

        Returns:
            Dict containing filtered search results
        """
        logger.info(f"MCP tool invoked: search_with_filters with query: {query}")

        try:
            # Parse list parameters (handle both JSON strings and actual lists)
            file_types_list = parse_list_param(file_types)
            directories_list = parse_list_param(directories)
            exclude_patterns_list = parse_list_param(exclude_patterns)
            authors_list = parse_list_param(authors)

            # Create search request with all filters
            request = SearchRequest(
                query=query,
                limit=limit,
                file_types=file_types_list,
                directories=directories_list,
                exclude_patterns=exclude_patterns_list,
                min_score=min_score,
                authors=authors_list,
                modified_after=modified_after,
                modified_before=modified_before,
            )

            # Perform search
            response = await search_code(request)

            # Format results
            formatted_results = []
            for result in response.results:
                formatted_result = {
                    "file_path": result.file_path,
                    "file_name": result.file_name,
                    "file_type": result.file_type,
                    "similarity_score": round(result.similarity_score, 3),
                    "confidence_score": round(result.confidence_score, 3),
                    "snippet_preview": (
                        result.snippet[:150] + "..."
                        if result.snippet and len(result.snippet) > 150
                        else result.snippet
                    ),
                }
                formatted_results.append(formatted_result)

            result = {
                "query": response.query,
                "total_results": response.total_results,
                "returned_results": len(formatted_results),
                "search_time_ms": round(response.search_time_ms, 2),
                "results": formatted_results,
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp,
            }

            logger.info(f"Filtered search completed: {response.total_results} results")
            return result

        except Exception as e:
            logger.error(f"Error in filtered search: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def search_statistics() -> Dict[str, Any]:
        """
        Get search statistics and performance metrics

        Returns comprehensive statistics about search operations including
        total searches, average response time, cache hit rate, and popular queries.

        Returns:
            Dict containing search statistics
        """
        logger.info("MCP tool invoked: search_statistics")

        try:
            stats = get_search_stats()

            result = {
                "total_searches": stats.total_searches,
                "average_response_time_ms": round(stats.average_response_time_ms, 2),
                "cache_hit_rate": round(stats.cache_hit_rate, 3),
                "popular_queries": stats.popular_queries[:10],
                "error_rate": round(stats.error_rate, 3),
                "timestamp": stats.timestamp,
            }

            logger.info("Search statistics retrieved successfully")
            return result

        except Exception as e:
            logger.error(f"Error getting search statistics: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def get_search_capabilities() -> Dict[str, Any]:
        """
        Get search capabilities and supported options

        Returns information about supported file types, common exclude patterns,
        and search configuration options.

        Returns:
            Dict containing search capabilities
        """
        logger.info("MCP tool invoked: get_search_capabilities")

        try:
            result = {
                "supported_file_types": get_supported_file_types(),
                "common_exclude_patterns": get_common_exclude_patterns(),
                "limits": {
                    "max_results": 100,
                    "default_results": 10,
                    "query_min_length": 1,
                    "query_max_length": 500,
                },
                "score_range": {"min": 0.0, "max": 1.0},
                "features": [
                    "Natural language queries",
                    "Vector similarity search",
                    "File type filtering",
                    "Directory filtering",
                    "Exclude patterns",
                    "Relevance ranking",
                    "Confidence scoring",
                    "Code snippet extraction",
                    "Result caching",
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info("Search capabilities retrieved successfully")
            return result

        except Exception as e:
            logger.error(f"Error getting search capabilities: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def update_ranking_weights(weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Update ranking weights for the search ranking engine.
        Allowed keys: similarity_weight, keyword_weight, file_size_weight, file_type_weight, freshness_weight, feedback_weight
        """
        logger.info("MCP tool invoked: update_ranking_weights")
        from src.search.ranking import get_ranking_service

        try:
            ranking = get_ranking_service()
            ranking.update_ranking_weights(weights)
            return {
                "success": True,
                "weights": ranking.get_ranking_weights(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to update ranking weights: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def provide_search_feedback(
        file_path: str, positive: bool = True
    ) -> Dict[str, Any]:
        """
        Provide feedback for a search result to improve ranking quality over time.
        """
        logger.info(f"MCP tool invoked: provide_search_feedback for {file_path}")
        try:
            from src.search.feedback import get_feedback_manager

            mgr = get_feedback_manager()
            mgr.register_feedback(file_path, positive)
            return {
                "success": True,
                "file_path": file_path,
                "positive": positive,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to register feedback: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("Search tools registered successfully")
