"""
MCP Indexing Tool

Provides indexing status and statistics via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.indexing.file_monitor import get_monitor_status
from src.indexing.file_indexer import get_indexer_stats
from src.indexing.queue import get_queue_status

logger = logging.getLogger(__name__)


def register_indexing_tools(mcp: FastMCP):
    """
    Register indexing tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def indexing_status() -> Dict[str, Any]:
        """
        Get comprehensive indexing status

        Returns comprehensive information about:
        - File monitor status
        - Indexing queue status
        - Indexing statistics
        - Database statistics

        Returns:
            Dict containing indexing status information
        """
        logger.info("MCP tool invoked: indexing_status")
        logger.debug("Gathering indexing status information")

        try:
            # Get monitor status
            monitor_status = get_monitor_status()

            # Get queue status
            queue_status = get_queue_status()

            # Get indexer stats
            indexer_stats = get_indexer_stats()

            # Get database stats
            try:
                from src.indexing.models import get_metadata_stats

                db_stats = await get_metadata_stats()
            except Exception as e:
                logger.warning(f"Could not get database stats: {e}")
                db_stats = {"error": str(e)}

            result = {
                "file_monitor": {
                    "running": monitor_status["running"],
                    "monitored_paths": monitor_status["monitored_paths"],
                    "ignore_patterns": monitor_status["ignore_patterns"],
                    "observer_alive": monitor_status["observer_alive"],
                },
                "indexing_queue": {
                    "processing": queue_status["processing"],
                    "queue_size": queue_status["queue_size"],
                    "current_item": queue_status["current_item"],
                    "stats": queue_status["stats"],
                },
                "indexer": {
                    "total_indexed": indexer_stats["total_indexed"],
                    "total_errors": indexer_stats["total_errors"],
                    "by_language": indexer_stats["by_language"],
                    "supported_languages": indexer_stats["supported_languages"],
                },
                "database": db_stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info("Indexing status retrieved successfully")
            logger.debug(f"Indexing status result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error getting indexing status: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def start_monitoring() -> Dict[str, Any]:
        """
        Start file system monitoring

        Returns:
            Dict containing operation result
        """
        logger.info("MCP tool invoked: start_monitoring")

        try:
            from src.indexing.file_monitor import start_file_monitor
            from src.indexing.queue import queue_file_change

            # Start monitor with queue callback
            await start_file_monitor(on_change_callback=queue_file_change)

            result = {
                "success": True,
                "message": "File monitoring started successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info("File monitoring started via MCP tool")
            return result

        except Exception as e:
            logger.error(f"Error starting monitoring: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def stop_monitoring() -> Dict[str, Any]:
        """
        Stop file system monitoring

        Returns:
            Dict containing operation result
        """
        logger.info("MCP tool invoked: stop_monitoring")

        try:
            from src.indexing.file_monitor import stop_file_monitor

            await stop_file_monitor()

            result = {
                "success": True,
                "message": "File monitoring stopped successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info("File monitoring stopped via MCP tool")
            return result

        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def trigger_initial_indexing() -> Dict[str, Any]:
        """
        Manually trigger initial indexing of existing files

        Scans all monitored paths and queues existing files for indexing.
        Useful for re-indexing the codebase or recovering from indexing failures.

        Returns:
            Dict containing operation result and statistics
        """
        logger.info("MCP tool invoked: trigger_initial_indexing")

        try:
            from src.indexing.initial_indexer import run_initial_indexing
            from src.indexing.queue import queue_file_change

            logger.info("Starting manual initial indexing...")
            stats = await run_initial_indexing(on_file_callback=queue_file_change)

            result = {
                "success": True,
                "message": "Initial indexing completed",
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Manual initial indexing completed: {stats['queued_files']} files queued"
            )
            return result

        except Exception as e:
            logger.error(f"Error during initial indexing: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("Indexing tools registered successfully")
