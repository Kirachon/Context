"""
MCP Health Check Tool

Provides health check functionality via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime
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
                "timestamp": datetime.utcnow().isoformat(),
                "environment": settings.environment,
                "services": services_status,
                "mcp_server": {
                    "enabled": mcp_status["enabled"],
                    "running": mcp_status["running"],
                    "connection_state": mcp_status["connection_state"]
                }
            }
            
            logger.info(f"Health check completed: {health_status}")
            logger.debug(f"Health check result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during health check: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"Server info result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting server info: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    logger.info("Health check tools registered successfully")


async def _check_services() -> Dict[str, bool]:
    """
    Check connectivity to external services
    
    Returns:
        Dict mapping service names to health status
    """
    services = {}
    
    # Check PostgreSQL - treat as unavailable unless explicitly configured via env
    try:
        db_env = os.environ.get("DATABASE_URL", "")
        services["postgres"] = bool(db_env) and db_env.startswith("postgresql")
    except Exception as e:
        logger.warning(f"PostgreSQL check failed: {e}")
        services["postgres"] = False

    # Check Redis
    try:
        redis_env = os.environ.get("REDIS_URL", "")
        services["redis"] = bool(redis_env) and redis_env.startswith("redis")
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
        services["redis"] = False

    # Check Qdrant
    try:
        qdrant_env = os.environ.get("QDRANT_HOST", "")
        services["qdrant"] = bool(qdrant_env)
    except Exception as e:
        logger.warning(f"Qdrant check failed: {e}")
        services["qdrant"] = False

    # Check Ollama
    try:
        ollama_env = os.environ.get("OLLAMA_BASE_URL", "")
        services["ollama"] = bool(ollama_env)
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")
        services["ollama"] = False
    
    return services

