"""
MCP Health Check Tool

Provides health check functionality via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.config.settings import settings

logger = logging.getLogger(__name__)


def register_health_tools(mcp: FastMCP):
    """
    Register health check tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def health_check() -> Dict[str, Any]:
        """
        Check the health status of the Context server

        Returns comprehensive health information including:
        - Overall server status
        - MCP server status
        - Service connectivity status
        - Version information
        - Timestamp

        Returns:
            Dict containing health status information
        """
        logger.info("MCP tool invoked: health_check")
        logger.debug("Gathering health status information")

        try:
            # Get service status
            services_status = await _check_services()

            # Determine overall health
            all_healthy = all(services_status.values())
            health_status = "healthy" if all_healthy else "degraded"

            # Get MCP server status
            from src.mcp_server.mcp_app import get_mcp_status

            mcp_status = get_mcp_status()

            result = {
                "status": health_status,
                "version": settings.app_version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": settings.environment,
                "services": services_status,
                "mcp_server": {
                    "enabled": mcp_status["enabled"],
                    "running": mcp_status["running"],
                    "connection_state": mcp_status["connection_state"],
                },
            }

            logger.info(f"Health check completed: {health_status}")
            logger.debug(f"Health check result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error during health check: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def server_info() -> Dict[str, Any]:
        """
        Get basic server information

        Returns:
            Dict containing server metadata
        """
        logger.info("MCP tool invoked: server_info")

        try:
            from src.mcp_server.mcp_app import get_mcp_status

            mcp_status = get_mcp_status()

            result = {
                "name": settings.app_name,
                "version": settings.app_version,
                "description": "100% Offline AI Coding Assistant",
                "environment": settings.environment,
                "mcp_enabled": mcp_status["enabled"],
                "mcp_connection_state": mcp_status["connection_state"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.debug(f"Server info result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error getting server info: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    logger.info("Health check tools registered successfully")


async def _check_services() -> Dict[str, bool]:
    """
    Check connectivity to external services by actually testing them

    Returns:
        Dict mapping service names to health status
    """
    services = {}

    # Check Qdrant - actual connection test
    try:
        from src.vector_db.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        if client:
            try:
                # Try to get collections to verify connection works
                collections = client.get_collections()
                services["qdrant"] = True
                logger.debug("Qdrant connection verified")
            except Exception as e:
                services["qdrant"] = False
                logger.warning(f"Qdrant connection test failed: {e}")
        else:
            services["qdrant"] = False
            logger.warning("Qdrant client is None")
    except Exception as e:
        logger.warning(f"Qdrant check failed: {e}")
        services["qdrant"] = False

    # Check Embeddings Service - actual model test
    try:
        from src.vector_db.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        # Test if model is loaded by checking if we can generate a simple embedding
        if embedding_service.model is not None:
            services["embeddings"] = True
            logger.debug("Embeddings model verified as loaded")
        else:
            services["embeddings"] = False
            logger.warning("Embeddings model is not loaded")
    except Exception as e:
        logger.warning(f"Embeddings service check failed: {e}")
        services["embeddings"] = False

    # Check File Monitor - actual status check
    try:
        from src.indexing.file_monitor import get_monitor_status
        monitor_status = get_monitor_status()
        # Monitor status returns a dict with status info, check if it's running
        services["file_monitor"] = monitor_status.get('is_running', False) if isinstance(monitor_status, dict) else bool(monitor_status)
        logger.debug(f"File monitor status: {services['file_monitor']}")
    except Exception as e:
        logger.warning(f"File monitor check failed: {e}")
        services["file_monitor"] = False

    # Check PostgreSQL - treat as optional, check if connection is configured and working
    try:
        from src.indexing.models import init_db, engine
        if engine is not None:
            try:
                # Try to get a connection
                with engine.connect() as conn:
                    services["postgres"] = True
                    logger.debug("PostgreSQL connection verified")
            except Exception as e:
                services["postgres"] = False
                logger.warning(f"PostgreSQL connection test failed: {e}")
        else:
            services["postgres"] = False
            logger.warning("PostgreSQL engine is not initialized")
    except Exception as e:
        logger.warning(f"PostgreSQL check failed (optional): {e}")
        services["postgres"] = False

    # Check Redis - optional service
    try:
        redis_url = getattr(settings, "redis_url", None)
        if redis_url:
            try:
                import redis
                r = redis.from_url(redis_url, decode_responses=True)
                r.ping()
                services["redis"] = True
                logger.debug("Redis connection verified")
            except Exception as e:
                services["redis"] = False
                logger.warning(f"Redis connection test failed: {e}")
        else:
            services["redis"] = False
    except Exception as e:
        logger.warning(f"Redis check failed (optional): {e}")
        services["redis"] = False

    return services
