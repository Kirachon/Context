"""
MCP Result Presentation Tools (Story 2-8)

Provides result presentation and navigation tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.result_presenter import (
    get_result_presenter, PresentationOptions, PresentationFormat, SortOrder
)
from src.search.result_navigator import get_result_navigator, NavigationFilter
from src.search.models import SearchResult
from pathlib import Path

logger = logging.getLogger(__name__)


def register_result_presentation_tools(mcp: FastMCP):
    """
    Register result presentation tools with MCP server
    
    Args:
        mcp: FastMCP server instance
    """
    
    @mcp.tool()
    async def format_search_results(
        results: List[Dict[str, Any]],
        format_type: str = "detailed",
        sort_order: str = "relevance",
        group_by_file: bool = False,
        show_context: bool = True
    ) -> Dict[str, Any]:
        """
        Format search results with advanced presentation options
        
        Formats search results using various presentation styles including
        compact, detailed, summary, tree, and timeline views.
        
        Args:
            results: List of search result dictionaries
            format_type: Presentation format (compact, detailed, summary, tree, timeline)
            sort_order: Sort order (relevance, alphabetical, date_modified, file_size, file_type)
            group_by_file: Group results by file
            show_context: Show content context
        
        Returns:
            Dict with formatted results
        """
        logger.info(f"MCP format search results invoked: {len(results)} results")
        
        try:
            # Convert dict results to SearchResult objects
            search_results = []
            for result_dict in results:
                search_result = SearchResult(
                    file_path=Path(result_dict.get('file_path', '')),
                    content=result_dict.get('content', ''),
                    score=result_dict.get('score', 0.0),
                    metadata=result_dict.get('metadata', {})
                )
                search_results.append(search_result)
            
            # Create presentation options
            options = PresentationOptions(
                format=PresentationFormat(format_type),
                sort_order=SortOrder(sort_order),
                group_by_file=group_by_file,
                show_context=show_context
            )
            
            # Format results
            presenter = get_result_presenter()
            formatted_results = presenter.present_results(search_results, options)
            
            # Convert to response format
            response_results = []
            for formatted in formatted_results:
                response_results.append({
                    "formatted_content": formatted.formatted_content,
                    "metadata": formatted.metadata,
                    "navigation_info": formatted.navigation_info
                })
            
            return {
                "success": True,
                "formatted_results": response_results,
                "total_count": len(response_results),
                "format_type": format_type,
                "sort_order": sort_order,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to format search results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @mcp.tool()
    async def navigate_search_results(
        results: List[Dict[str, Any]],
        action: str,
        index: Optional[int] = None,
        filter_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Navigate through search results
        
        Provides navigation capabilities including jumping to specific results,
        filtering, and exploring related results.
        
        Args:
            results: List of search result dictionaries
            action: Navigation action (jump, next, previous, back, filter, related)
            index: Target index for jump action
            filter_options: Filter options for filtering action
        
        Returns:
            Dict with navigation results
        """
        logger.info(f"MCP navigate search results invoked: action={action}")
        
        try:
            # Convert dict results to SearchResult objects
            search_results = []
            for result_dict in results:
                search_result = SearchResult(
                    file_path=Path(result_dict.get('file_path', '')),
                    content=result_dict.get('content', ''),
                    score=result_dict.get('score', 0.0),
                    metadata=result_dict.get('metadata', {})
                )
                search_results.append(search_result)
            
            navigator = get_result_navigator()
            navigator.set_results(search_results)
            
            result = None
            if action == "jump" and index is not None:
                result = navigator.jump_to_result(index)
            elif action == "next":
                result = navigator.next_result()
            elif action == "previous":
                result = navigator.previous_result()
            elif action == "back":
                result = navigator.go_back()
            elif action == "filter" and filter_options:
                nav_filter = NavigationFilter(
                    file_types=filter_options.get('file_types'),
                    directories=filter_options.get('directories'),
                    score_threshold=filter_options.get('score_threshold'),
                    content_pattern=filter_options.get('content_pattern'),
                    exclude_patterns=filter_options.get('exclude_patterns')
                )
                filtered_results = navigator.filter_results(search_results, nav_filter)
                return {
                    "success": True,
                    "action": action,
                    "filtered_results": [
                        {
                            "file_path": str(r.file_path),
                            "content": r.content,
                            "score": r.score,
                            "metadata": r.metadata
                        }
                        for r in filtered_results
                    ],
                    "filtered_count": len(filtered_results),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            elif action == "related":
                current = navigator.get_current_result()
                if current:
                    related = navigator.find_related_results(current)
                    return {
                        "success": True,
                        "action": action,
                        "current_result": str(current.file_path),
                        "related_results": [
                            {
                                "file_path": str(r.file_path),
                                "content": r.content,
                                "score": r.score
                            }
                            for r in related
                        ],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            
            # Get navigation summary
            summary = navigator.get_navigation_summary()
            
            response = {
                "success": True,
                "action": action,
                "navigation_summary": summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if result:
                response["current_result"] = {
                    "file_path": str(result.file_path),
                    "content": result.content,
                    "score": result.score,
                    "metadata": result.metadata
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to navigate search results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @mcp.tool()
    async def expand_result_context(
        file_path: str,
        content: str,
        lines_before: int = 5,
        lines_after: int = 5
    ) -> Dict[str, Any]:
        """
        Expand context around a search result
        
        Provides expanded context around a search result by reading
        additional lines from the source file.
        
        Args:
            file_path: Path to the file
            content: Original result content
            lines_before: Number of lines to show before
            lines_after: Number of lines to show after
        
        Returns:
            Dict with expanded context
        """
        logger.info(f"MCP expand result context invoked: {file_path}")
        
        try:
            # Create a mock SearchResult
            search_result = SearchResult(
                file_path=Path(file_path),
                content=content,
                score=1.0,
                metadata={}
            )
            
            navigator = get_result_navigator()
            expanded_context = navigator.expand_context(
                search_result, lines_before, lines_after
            )
            
            return {
                "success": True,
                "file_path": file_path,
                "original_content": content,
                "expanded_context": expanded_context,
                "lines_before": lines_before,
                "lines_after": lines_after,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to expand result context: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
