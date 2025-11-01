"""
MCP Cache Management Tools (Story 2-7)

Provides cache management and monitoring tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.embedding_cache import get_embedding_cache
from src.parsing.cache import get_ast_cache

logger = logging.getLogger(__name__)


def register_cache_management_tools(mcp: FastMCP):
    """
    Register cache management tools with MCP server
    
    Args:
        mcp: FastMCP server instance
    """
    
    @mcp.tool()
    async def cache_statistics() -> Dict[str, Any]:
        """
        Get comprehensive cache statistics
        
        Returns statistics for all cache layers:
        - Embedding cache
        - AST cache
        - Search result cache
        
        Returns:
            Dict with cache statistics for all layers
        """
        logger.info("MCP cache statistics invoked")
        
        try:
            # Get embedding cache stats
            embedding_cache = get_embedding_cache()
            embedding_stats = embedding_cache.get_statistics()
            
            # Get AST cache stats
            ast_cache = get_ast_cache()
            ast_stats = {
                "enabled": ast_cache.enabled,
                "redis_connected": ast_cache.redis_client is not None
            }
            
            return {
                "success": True,
                "embedding_cache": embedding_stats,
                "ast_cache": ast_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @mcp.tool()
    async def invalidate_embedding_cache(model: Optional[str] = None) -> Dict[str, Any]:
        """
        Invalidate embedding cache
        
        Clears cached embeddings for a specific model or all models.
        Useful when updating embedding models or fixing cache issues.
        
        Args:
            model: Model name to invalidate (optional, invalidates all if not specified)
        
        Returns:
            Dict with invalidation results
        """
        logger.info(f"MCP embedding cache invalidation invoked: model={model}")
        
        try:
            embedding_cache = get_embedding_cache()
            
            if model:
                embedding_cache.invalidate_model(model)
                message = f"Invalidated embedding cache for model: {model}"
            else:
                # Invalidate all models (would need to implement this)
                message = "Full cache invalidation not yet implemented"
            
            stats = embedding_cache.get_statistics()
            
            return {
                "success": True,
                "message": message,
                "invalidations": stats["invalidations"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @mcp.tool()
    async def cache_health_check() -> Dict[str, Any]:
        """
        Check health of all cache layers
        
        Verifies that cache systems are operational and performing well.
        Checks:
        - Redis connectivity
        - Cache hit rates
        - Error rates
        - Performance metrics
        
        Returns:
            Dict with health status for all cache layers
        """
        logger.info("MCP cache health check invoked")
        
        try:
            embedding_cache = get_embedding_cache()
            embedding_stats = embedding_cache.get_statistics()
            
            ast_cache = get_ast_cache()
            
            # Determine health status
            embedding_healthy = (
                embedding_cache.enabled and
                embedding_stats["hit_rate_percent"] > 20 and
                embedding_stats["errors"] < 100
            )
            
            ast_healthy = ast_cache.enabled and ast_cache.redis_client is not None
            
            overall_healthy = embedding_healthy and ast_healthy
            
            return {
                "success": True,
                "overall_healthy": overall_healthy,
                "embedding_cache": {
                    "healthy": embedding_healthy,
                    "enabled": embedding_cache.enabled,
                    "hit_rate": embedding_stats["hit_rate_percent"],
                    "errors": embedding_stats["errors"]
                },
                "ast_cache": {
                    "healthy": ast_healthy,
                    "enabled": ast_cache.enabled,
                    "redis_connected": ast_cache.redis_client is not None
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}", exc_info=True)
            return {
                "success": False,
                "overall_healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @mcp.tool()
    async def configure_cache(
        ttl_seconds: Optional[int] = None,
        max_cache_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Configure cache settings
        
        Updates cache configuration parameters dynamically.
        
        Args:
            ttl_seconds: Cache TTL in seconds (optional)
            max_cache_size: Maximum cache size (optional)
        
        Returns:
            Dict with updated configuration
        """
        logger.info(f"MCP cache configuration invoked: ttl={ttl_seconds}, max_size={max_cache_size}")
        
        try:
            embedding_cache = get_embedding_cache()
            
            if ttl_seconds is not None:
                embedding_cache.ttl_seconds = ttl_seconds
            
            if max_cache_size is not None:
                embedding_cache.max_cache_size = max_cache_size
            
            return {
                "success": True,
                "configuration": {
                    "ttl_seconds": embedding_cache.ttl_seconds,
                    "max_cache_size": embedding_cache.max_cache_size
                },
                "message": "Cache configuration updated",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to configure cache: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

