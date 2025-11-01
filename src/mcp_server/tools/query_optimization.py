"""
MCP Query Optimization Tools (Story 2-7, Phase 3)

Provides query optimization and profiling tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.pagination import CursorPaginator, StreamingPaginator
from src.search.query_profiler import get_query_profiler

logger = logging.getLogger(__name__)


def register_query_optimization_tools(mcp: FastMCP):
    """
    Register query optimization tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def paginate_results(
        items: List[Dict[str, Any]],
        cursor: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Paginate search results using cursor-based pagination

        Provides efficient pagination for large result sets.

        Args:
            items: List of result items
            cursor: Pagination cursor (optional)
            page_size: Page size (optional, default 20)

        Returns:
            Dict with paginated results and cursors
        """
        logger.info(f"MCP paginate results invoked: {len(items)} items")

        try:
            paginator = CursorPaginator(page_size=20, max_page_size=100)
            result = paginator.paginate(items, cursor, page_size)

            return {
                "success": True,
                "items": result.items,
                "total_count": result.total_count,
                "page_size": result.page_size,
                "current_offset": result.current_offset,
                "has_next": result.has_next,
                "has_previous": result.has_previous,
                "next_cursor": result.next_cursor,
                "previous_cursor": result.previous_cursor,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to paginate results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def stream_results(
        items: List[Dict[str, Any]], chunk_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Stream search results in chunks

        Provides memory-efficient streaming for large result sets.

        Args:
            items: List of result items
            chunk_size: Size of each chunk (optional, default 50)

        Returns:
            Dict with streaming information
        """
        logger.info(f"MCP stream results invoked: {len(items)} items")

        try:
            streamer = StreamingPaginator(chunk_size=chunk_size or 50)

            chunks = []
            for chunk_data in streamer.stream_with_progress(items):
                chunks.append(chunk_data)

            return {
                "success": True,
                "total_items": len(items),
                "chunk_count": len(chunks),
                "chunks": chunks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to stream results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_performance_profile() -> Dict[str, Any]:
        """
        Get query performance profile

        Returns comprehensive performance metrics including:
        - Average query duration
        - Cache hit rate
        - Slow query count
        - Phase-specific timings

        Returns:
            Dict with performance profile
        """
        logger.info("MCP query performance profile invoked")

        try:
            profiler = get_query_profiler()
            stats = profiler.get_statistics()
            slow_queries = profiler.get_slow_queries(limit=5)
            recommendations = profiler.get_optimization_recommendations()

            return {
                "success": True,
                "statistics": stats,
                "slow_queries": slow_queries,
                "recommendations": recommendations,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get query profile: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def clear_query_profiles() -> Dict[str, Any]:
        """
        Clear query performance profiles

        Clears all stored query profiles and resets statistics.

        Returns:
            Dict with clear confirmation
        """
        logger.info("MCP clear query profiles invoked")

        try:
            profiler = get_query_profiler()
            profiler.clear_profiles()

            return {
                "success": True,
                "message": "Query profiles cleared",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to clear profiles: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
