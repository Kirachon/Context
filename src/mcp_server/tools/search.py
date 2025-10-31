"""
MCP Search Tools

Provides semantic search operations via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.semantic_search import search_code, get_search_stats
from src.search.models import SearchRequest
from src.search.filters import get_supported_file_types, get_common_exclude_patterns

logger = logging.getLogger(__name__)


def register_search_tools(mcp: FastMCP):
    """
    Register search tools with MCP server
    
    Args:
        mcp: FastMCP server instance
    """
    
    @mcp.tool()
    async def semantic_search(
        query: str,
        limit: int = 10,
        file_types: Optional[List[str]] = None,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search codebase using natural language query
        
        Performs semantic search over indexed code files using vector embeddings.
        Returns relevant code files ranked by similarity.
        
        Args:
            query: Natural language search query (e.g., "authentication functions")
            limit: Maximum number of results to return (1-100, default: 10)
            file_types: Filter by file extensions (e.g., [".py", ".js"])
            min_score: Minimum similarity score (0.0-1.0, default: 0.0)
        
        Returns:
            Dict containing search results with file paths, scores, and snippets
        """
        logger.info(f"MCP tool invoked: semantic_search with query: {query}")
        
        try:
            # Create search request
            request = SearchRequest(
                query=query,
                limit=limit,
                file_types=file_types,
                min_score=min_score
            )
            
            # Perform search
            response = await search_code(request)
            
            # Format results for MCP
            formatted_results = []
            for result in response.results:
                formatted_result = {
                    "file_path": result.file_path,
                    "file_name": result.file_name,
                    "file_type": result.file_type,
                    "similarity_score": round(result.similarity_score, 3),
                    "confidence_score": round(result.confidence_score, 3),
                    "file_size": result.file_size,
                    "snippet": result.snippet[:200] + "..." if result.snippet and len(result.snippet) > 200 else result.snippet
                }
                formatted_results.append(formatted_result)
            
            result = {
                "query": response.query,
                "total_results": response.total_results,
                "returned_results": len(formatted_results),
                "search_time_ms": round(response.search_time_ms, 2),
                "results": formatted_results,
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp
            }
            
            logger.info(f"Semantic search completed: {response.total_results} results in {response.search_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool()
    async def search_with_filters(
        query: str,
        limit: int = 10,
        file_types: Optional[List[str]] = None,
        directories: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search codebase with advanced filtering options
        
        Performs semantic search with comprehensive filtering by file type,
        directory, and exclude patterns.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results (1-100, default: 10)
            file_types: Filter by file extensions (e.g., [".py", ".js"])
            directories: Filter by directory paths (e.g., ["src", "lib"])
            exclude_patterns: Exclude patterns (e.g., ["test", "__pycache__"])
            min_score: Minimum similarity score (0.0-1.0, default: 0.0)
        
        Returns:
            Dict containing filtered search results
        """
        logger.info(f"MCP tool invoked: search_with_filters with query: {query}")
        
        try:
            # Create search request with all filters
            request = SearchRequest(
                query=query,
                limit=limit,
                file_types=file_types,
                directories=directories,
                exclude_patterns=exclude_patterns,
                min_score=min_score
            )
            
            # Perform search
            response = await search_code(request)
            
            # Format results
            formatted_results = []
            for result in response.results:
                formatted_result = {
                    "file_path": result.file_path,
                    "file_name": result.file_name,
                    "file_type": result.file_type,
                    "similarity_score": round(result.similarity_score, 3),
                    "confidence_score": round(result.confidence_score, 3),
                    "snippet_preview": result.snippet[:150] + "..." if result.snippet and len(result.snippet) > 150 else result.snippet
                }
                formatted_results.append(formatted_result)
            
            result = {
                "query": response.query,
                "total_results": response.total_results,
                "returned_results": len(formatted_results),
                "search_time_ms": round(response.search_time_ms, 2),
                "results": formatted_results,
                "filters_applied": response.filters_applied,
                "timestamp": response.timestamp
            }
            
            logger.info(f"Filtered search completed: {response.total_results} results")
            return result
            
        except Exception as e:
            logger.error(f"Error in filtered search: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool()
    async def search_statistics() -> Dict[str, Any]:
        """
        Get search statistics and performance metrics
        
        Returns comprehensive statistics about search operations including
        total searches, average response time, cache hit rate, and popular queries.
        
        Returns:
            Dict containing search statistics
        """
        logger.info("MCP tool invoked: search_statistics")
        
        try:
            stats = get_search_stats()
            
            result = {
                "total_searches": stats.total_searches,
                "average_response_time_ms": round(stats.average_response_time_ms, 2),
                "cache_hit_rate": round(stats.cache_hit_rate, 3),
                "popular_queries": stats.popular_queries[:10],
                "error_rate": round(stats.error_rate, 3),
                "timestamp": stats.timestamp
            }
            
            logger.info("Search statistics retrieved successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error getting search statistics: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool()
    async def get_search_capabilities() -> Dict[str, Any]:
        """
        Get search capabilities and supported options
        
        Returns information about supported file types, common exclude patterns,
        and search configuration options.
        
        Returns:
            Dict containing search capabilities
        """
        logger.info("MCP tool invoked: get_search_capabilities")
        
        try:
            result = {
                "supported_file_types": get_supported_file_types(),
                "common_exclude_patterns": get_common_exclude_patterns(),
                "limits": {
                    "max_results": 100,
                    "default_results": 10,
                    "query_min_length": 1,
                    "query_max_length": 500
                },
                "score_range": {
                    "min": 0.0,
                    "max": 1.0
                },
                "features": [
                    "Natural language queries",
                    "Vector similarity search",
                    "File type filtering",
                    "Directory filtering",
                    "Exclude patterns",
                    "Relevance ranking",
                    "Confidence scoring",
                    "Code snippet extraction",
                    "Result caching"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Search capabilities retrieved successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error getting search capabilities: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    logger.info("Search tools registered successfully")

