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

from src.config.settings import settings

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
        - Unique files indexed (actual file count from database)
        - Total indexing operations performed (may be higher due to re-indexing)
        - File monitor status
        - Indexing queue status
        - Breakdown by component (FileIndexer, ASTIndexer, Queue)

        The key metrics to understand:
        - unique_files_indexed: Actual number of distinct files in the system
        - total_operations: Total number of indexing operations (includes re-indexing)
        - Operations count will be higher than unique files due to file modifications,
          multiple indexing passes, and different indexing components

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

            # Get database stats (optional)
            if getattr(settings, "postgres_enabled", False) and getattr(settings, "database_url", None):
                try:
                    from src.indexing.models import get_metadata_stats
                    db_stats = await get_metadata_stats()
                    unique_files_count = db_stats.get("total_files", 0)
                except Exception as e:
                    logger.warning(f"Could not get database stats: {e}")
                    db_stats = {"error": str(e)}
                    unique_files_count = 0
            else:
                db_stats = {"disabled": True, "message": "PostgreSQL disabled; running in vector-only mode"}
                unique_files_count = 0

            # Get AST indexer stats
            try:
                from src.indexing.ast_indexer import get_ast_indexer

                ast_indexer = get_ast_indexer()
                ast_stats = ast_indexer.get_stats()
            except Exception as e:
                logger.warning(f"Could not get AST indexer stats: {e}")
                ast_stats = {"error": str(e)}

            # Calculate total operations across all components
            total_operations = (
                indexer_stats.get("total_indexed", 0)
                + queue_status["stats"].get("total_processed", 0)
                + ast_stats.get("files_indexed", 0)
            )

            result = {
                # PRIMARY METRICS - What users care about
                "summary": {
                    "unique_files_indexed": unique_files_count,
                    "total_operations": total_operations,
                    "description": f"{unique_files_count} unique files indexed with {total_operations} total operations",
                },
                # Back-compat: expose raw FileIndexer stats under 'indexer' key for tests/clients
                "indexer": indexer_stats,
                # Detailed breakdown
                "operations_by_component": {
                    "file_indexer": {
                        "operations": indexer_stats.get("total_indexed", 0),
                        "errors": indexer_stats.get("total_errors", 0),
                        "by_language": indexer_stats.get("by_language", {}),
                        "description": "Semantic embedding operations",
                    },
                    "ast_indexer": {
                        "operations": ast_stats.get("files_indexed", 0),
                        "symbols_indexed": ast_stats.get("symbols_indexed", 0),
                        "classes_indexed": ast_stats.get("classes_indexed", 0),
                        "imports_indexed": ast_stats.get("imports_indexed", 0),
                        "errors": ast_stats.get("errors", 0),
                        "description": "Code structure parsing operations",
                    },
                    "queue": {
                        "operations": queue_status["stats"].get("total_processed", 0),
                        "unique_files": queue_status["stats"].get(
                            "unique_files_processed", 0
                        ),
                        "duplicates_skipped": queue_status["stats"].get(
                            "duplicate_requests_skipped", 0
                        ),
                        "failed": queue_status["stats"].get("total_failed", 0),
                        "description": "Queue processing operations",
                    },
                },
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
                },
                "database": db_stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Indexing status: {unique_files_count} unique files, {total_operations} operations"
            )
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
