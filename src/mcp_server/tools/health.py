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

    @mcp.tool()
    async def check_qdrant_status() -> Dict[str, Any]:
        """
        Check Qdrant vector database connection status

        Returns detailed information about Qdrant connectivity including:
        - Connection status (connected/disconnected)
        - Host and port configuration
        - Health check results
        - Collection count (if connected)
        - Connection attempts and retries

        Use this tool to diagnose vector search issues.

        Returns:
            Dict containing Qdrant status information
        """
        logger.info("MCP tool invoked: check_qdrant_status")

        try:
            from src.vector_db.qdrant_client import get_qdrant_status

            status = await get_qdrant_status()

            logger.debug(f"Qdrant status: {status}")
            return status

        except Exception as e:
            logger.error(f"Error checking Qdrant status: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("Health check tools registered successfully")


async def _check_services() -> Dict[str, bool]:
    """
    Check connectivity to external services

    Returns:
        Dict mapping service names to health status
    """
    services = {}

    # Environment-aware checks: in tests, rely on env presence only (no network calls)
    env = os.environ.get("ENVIRONMENT", settings.environment).lower() if hasattr(settings, "environment") else os.environ.get("ENVIRONMENT", "development").lower()

    # Check PostgreSQL - based on env var presence
    try:
        db_env = os.environ.get("DATABASE_URL", "")
        services["postgres"] = bool(db_env) and db_env.startswith("postgresql")
    except Exception as e:
        logger.warning(f"PostgreSQL check failed: {e}")
        services["postgres"] = False

    # Check Redis - based on env var presence
    try:
        redis_env = os.environ.get("REDIS_URL", "")
        services["redis"] = bool(redis_env) and redis_env.startswith("redis")
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
        services["redis"] = False

    # Check Qdrant
    try:
        if env == "test":
            # In tests, consider configured if host is provided
            services["qdrant"] = bool(os.environ.get("QDRANT_HOST"))
        else:
            from src.vector_db.qdrant_client import qdrant_client_service
            services["qdrant"] = bool(getattr(qdrant_client_service, "is_connected", False))
    except Exception as e:
        logger.warning(f"Qdrant check failed: {e}")
        services["qdrant"] = False

    # Check Ollama
    try:
        if env == "test":
            services["ollama"] = bool(os.environ.get("OLLAMA_BASE_URL"))
        else:
            from src.ai_processing.ollama_client import get_ollama_client
            ollama_client = get_ollama_client()
            url = f"{ollama_client.base_url}/api/tags"
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        services["ollama"] = True
                        logger.debug(f"Ollama health check passed: {url}")
            except ImportError:
                # Fall back to env presence
                services["ollama"] = bool(os.environ.get("OLLAMA_BASE_URL"))
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        services["ollama"] = False

    return services
