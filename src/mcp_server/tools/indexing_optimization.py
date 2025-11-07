"""
MCP Indexing Optimization Tools (Story 2-7, Phase 2)

Provides indexing optimization and monitoring tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Union

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.indexing.progressive_indexer import get_progressive_indexer, IndexingPriority
from src.indexing.indexing_metrics import get_indexing_metrics
from src.mcp_server.utils.param_parsing import parse_list_param

logger = logging.getLogger(__name__)


def register_indexing_optimization_tools(mcp: FastMCP):
    """
    Register indexing optimization tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def indexing_progress() -> Dict[str, Any]:
        """
        Get current indexing progress

        Returns progress information including:
        - Total tasks
        - Completed tasks
        - Failed tasks
        - Progress percentage
        - Current batch size
        - Pause status

        Returns:
            Dict with progress information
        """
        logger.info("MCP indexing progress invoked")

        try:
            indexer = get_progressive_indexer()
            progress = indexer.get_progress()

            return {
                "success": True,
                "progress": progress,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get indexing progress: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def indexing_metrics() -> Dict[str, Any]:
        """
        Get indexing performance metrics

        Returns comprehensive metrics including:
        - Batch statistics
        - Throughput (files per second)
        - Success/failure rates
        - Performance trends

        Returns:
            Dict with metrics data
        """
        logger.info("MCP indexing metrics invoked")

        try:
            indexer = get_progressive_indexer()
            metrics_collector = get_indexing_metrics()

            return {
                "success": True,
                "indexer_metrics": indexer.get_metrics(),
                "performance_metrics": metrics_collector.get_statistics(),
                "batch_history": metrics_collector.get_batch_history(limit=5),
                "performance_trend": metrics_collector.get_performance_trend(),
                "optimal_batch_size": metrics_collector.get_optimal_batch_size(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get indexing metrics: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def pause_indexing() -> Dict[str, Any]:
        """
        Pause indexing operations

        Pauses the indexing process while preserving queue state.
        Can be resumed later.

        Returns:
            Dict with pause confirmation
        """
        logger.info("MCP pause indexing invoked")

        try:
            indexer = get_progressive_indexer()
            indexer.pause()

            return {
                "success": True,
                "message": "Indexing paused",
                "paused": indexer.paused,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to pause indexing: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def resume_indexing() -> Dict[str, Any]:
        """
        Resume indexing operations

        Resumes paused indexing process.

        Returns:
            Dict with resume confirmation
        """
        logger.info("MCP resume indexing invoked")

        try:
            indexer = get_progressive_indexer()
            indexer.resume()

            return {
                "success": True,
                "message": "Indexing resumed",
                "paused": indexer.paused,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to resume indexing: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def add_indexing_tasks(
        file_paths: Union[str, List[str]], priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Add files to indexing queue

        Adds one or more files to the indexing queue with specified priority.

        Args:
            file_paths: List of file paths to index. Can be a JSON string or list.
            priority: Priority level (critical, high, normal, low)

        Returns:
            Dict with task addition results
        """
        # Parse list parameters (handle both JSON strings and actual lists)
        file_paths_list = parse_list_param(file_paths)

        if not file_paths_list:
            return {
                "success": False,
                "error": "No valid file paths provided",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        logger.info(
            f"MCP add indexing tasks invoked: {len(file_paths_list)} files, priority={priority}"
        )

        try:
            # Parse priority
            priority_map = {
                "critical": IndexingPriority.CRITICAL,
                "high": IndexingPriority.HIGH,
                "normal": IndexingPriority.NORMAL,
                "low": IndexingPriority.LOW,
            }

            priority_enum = priority_map.get(priority.lower(), IndexingPriority.NORMAL)

            indexer = get_progressive_indexer()
            indexer.add_tasks_batch(file_paths_list, priority_enum)

            progress = indexer.get_progress()

            return {
                "success": True,
                "message": f"Added {len(file_paths_list)} tasks to indexing queue",
                "files_added": len(file_paths_list),
                "priority": priority,
                "progress": progress,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to add indexing tasks: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def optimize_batch_size() -> Dict[str, Any]:
        """
        Optimize batch size based on performance data

        Analyzes performance metrics and recommends optimal batch size.

        Returns:
            Dict with optimization recommendations
        """
        logger.info("MCP optimize batch size invoked")

        try:
            indexer = get_progressive_indexer()
            metrics_collector = get_indexing_metrics()

            optimal_size = metrics_collector.get_optimal_batch_size()
            current_size = indexer.current_batch_size

            # Apply recommendation if significantly different
            if abs(optimal_size - current_size) > 2:
                indexer.current_batch_size = optimal_size
                applied = True
            else:
                applied = False

            return {
                "success": True,
                "current_batch_size": current_size,
                "optimal_batch_size": optimal_size,
                "applied": applied,
                "message": f"Batch size {'updated' if applied else 'already optimal'}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to optimize batch size: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
