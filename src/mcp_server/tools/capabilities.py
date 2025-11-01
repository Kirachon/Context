"""
MCP Capabilities Tool

Provides server capabilities listing via MCP protocol.
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


def register_capability_tools(mcp: FastMCP):
    """
    Register capability listing tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def list_capabilities() -> Dict[str, Any]:
        """
        List all available server capabilities

        Returns comprehensive information about:
        - Available MCP tools
        - Server features
        - Configuration options
        - Supported operations

        Returns:
            Dict containing capabilities information
        """
        logger.info("MCP tool invoked: list_capabilities")
        logger.debug("Gathering capabilities information")

        try:
            from src.mcp_server.mcp_app import get_mcp_status

            mcp_status = get_mcp_status()

            result = {
                "server": {
                    "name": settings.mcp_server_name,
                    "version": settings.mcp_server_version,
                    "status": mcp_status["connection_state"],
                },
                "capabilities": settings.mcp_capabilities,
                "tools": [
                    {
                        "name": "health_check",
                        "description": "Check server health status",
                        "category": "monitoring",
                    },
                    {
                        "name": "server_info",
                        "description": "Get basic server information",
                        "category": "information",
                    },
                    {
                        "name": "list_capabilities",
                        "description": "List all available capabilities",
                        "category": "information",
                    },
                    {
                        "name": "get_configuration",
                        "description": "Get server configuration details",
                        "category": "configuration",
                    },
                ],
                "features": {
                    "semantic_search": "Planned - Not yet implemented",
                    "code_intelligence": "Planned - Not yet implemented",
                    "prompt_enhancement": "Planned - Not yet implemented",
                    "local_processing": "Enabled - 100% offline operation",
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Capabilities listed: {len(result['tools'])} tools available")
            logger.debug(f"Capabilities result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error listing capabilities: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    @mcp.tool()
    async def get_configuration() -> Dict[str, Any]:
        """
        Get server configuration details

        Returns non-sensitive configuration information including:
        - Server settings
        - Performance parameters
        - Feature flags

        Returns:
            Dict containing configuration information
        """
        logger.info("MCP tool invoked: get_configuration")
        logger.debug("Gathering configuration information")

        try:
            result = {
                "server": {
                    "host": settings.host,
                    "port": settings.port,
                    "environment": settings.environment,
                    "workers": settings.workers,
                },
                "mcp": {
                    "enabled": settings.mcp_enabled,
                    "server_name": settings.mcp_server_name,
                    "connection_timeout": settings.mcp_connection_timeout,
                    "max_retries": settings.mcp_max_retries,
                },
                "performance": {
                    "max_search_results": settings.max_search_results,
                    "cache_ttl_seconds": settings.cache_ttl_seconds,
                    "indexing_batch_size": settings.indexing_batch_size,
                },
                "logging": {"level": settings.log_level, "format": settings.log_format},
                "hardware_requirements": {
                    "min_memory_gb": settings.min_memory_gb,
                    "min_cpu_cores": settings.min_cpu_cores,
                    "min_disk_space_gb": settings.min_disk_space_gb,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info("Configuration information retrieved successfully")
            logger.debug(f"Configuration result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error getting configuration: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    logger.info("Capability tools registered successfully")
