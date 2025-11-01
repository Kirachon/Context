"""
MCP Vector Tools

Provides vector database operations via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.vector_db.qdrant_client import get_qdrant_status
from src.vector_db.embeddings import get_embedding_stats
from src.vector_db.vector_store import get_vector_stats, search_vectors
from src.vector_db.collections import list_collections, get_collection_stats

logger = logging.getLogger(__name__)


def register_vector_tools(mcp: FastMCP):
    """
    Register vector database tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def vector_status() -> Dict[str, Any]:
        """
        Get comprehensive vector database status

        Returns comprehensive information about:
        - Qdrant connection status
        - Embedding service status
        - Vector store statistics
        - Collection information

        Returns:
            Dict containing vector database status
        """
        logger.info("MCP tool invoked: vector_status")
        logger.debug("Gathering vector database status information")

        try:
            # Get Qdrant status
            qdrant_status = await get_qdrant_status()

            # Get embedding stats
            embedding_stats = get_embedding_stats()

            # Get vector store stats
            vector_stats = get_vector_stats()

            # Get collection information
            collection_names = await list_collections()
            collections_info = []

            for collection_name in collection_names:
                collection_stats = await get_collection_stats(collection_name)
                if collection_stats:
                    collections_info.append(collection_stats)

            result = {
                "qdrant": {
                    "connected": qdrant_status.get("connected", False),
                    "host": qdrant_status.get("host"),
                    "port": qdrant_status.get("port"),
                    "health": qdrant_status.get("health", {}),
                },
                "embeddings": {
                    "model_name": embedding_stats.get("model_name"),
                    "embedding_dim": embedding_stats.get("embedding_dim"),
                    "model_loaded": embedding_stats.get("model_loaded", False),
                    "cache_size": embedding_stats.get("cache_size", 0),
                },
                "vector_store": {
                    "vectors_stored": vector_stats.get("vectors_stored", 0),
                    "vectors_retrieved": vector_stats.get("vectors_retrieved", 0),
                    "vectors_deleted": vector_stats.get("vectors_deleted", 0),
                    "batch_operations": vector_stats.get("batch_operations", 0),
                    "errors": vector_stats.get("errors", 0),
                },
                "collections": collections_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info("Vector database status retrieved successfully")
            logger.debug(f"Vector status result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error getting vector database status: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def search_code(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for code using natural language query

        Args:
            query: Natural language search query
            limit: Maximum number of results to return

        Returns:
            Dict containing search results
        """
        logger.info(f"MCP tool invoked: search_code with query: {query}")

        try:
            from src.vector_db.embeddings import generate_embedding

            # Generate embedding for query
            query_embedding = await generate_embedding(query)

            if not query_embedding:
                return {
                    "error": "Failed to generate embedding for query",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Search vectors
            search_results = await search_vectors(query_embedding, limit)

            # Format results
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "file_path": result["payload"].get("file_path"),
                    "file_name": result["payload"].get("file_name"),
                    "file_type": result["payload"].get("file_type"),
                    "similarity_score": result["score"],
                    "size": result["payload"].get("size"),
                }
                formatted_results.append(formatted_result)

            result = {
                "query": query,
                "results_count": len(formatted_results),
                "results": formatted_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Code search completed: {len(formatted_results)} results")
            return result

        except Exception as e:
            logger.error(f"Error searching code: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def list_vector_collections() -> Dict[str, Any]:
        """
        List all vector collections

        Returns:
            Dict containing collection information
        """
        logger.info("MCP tool invoked: list_vector_collections")

        try:
            collection_names = await list_collections()
            collections_info = []

            for collection_name in collection_names:
                collection_stats = await get_collection_stats(collection_name)
                if collection_stats:
                    collections_info.append(collection_stats)

            result = {
                "collections_count": len(collections_info),
                "collections": collections_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Listed {len(collections_info)} vector collections")
            return result

        except Exception as e:
            logger.error(f"Error listing vector collections: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @mcp.tool()
    async def vector_health_check() -> Dict[str, Any]:
        """
        Perform comprehensive vector database health check

        Returns:
            Dict containing health check results
        """
        logger.info("MCP tool invoked: vector_health_check")

        try:
            # Check Qdrant connection
            qdrant_status = await get_qdrant_status()
            qdrant_healthy = qdrant_status.get("connected", False)

            # Check embedding service
            embedding_stats = get_embedding_stats()
            embeddings_healthy = embedding_stats.get("model_loaded", False)

            # Check collections
            collections = await list_collections()
            collections_healthy = len(collections) > 0

            # Overall health
            overall_healthy = qdrant_healthy and embeddings_healthy

            result = {
                "overall_status": "healthy" if overall_healthy else "unhealthy",
                "checks": {
                    "qdrant_connection": {
                        "status": "healthy" if qdrant_healthy else "unhealthy",
                        "details": qdrant_status,
                    },
                    "embedding_service": {
                        "status": "healthy" if embeddings_healthy else "unhealthy",
                        "details": embedding_stats,
                    },
                    "collections": {
                        "status": "healthy" if collections_healthy else "warning",
                        "count": len(collections),
                        "names": collections,
                    },
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Vector health check completed: {result['overall_status']}")
            return result

        except Exception as e:
            logger.error(f"Error during vector health check: {e}", exc_info=True)
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("Vector database tools registered successfully")
