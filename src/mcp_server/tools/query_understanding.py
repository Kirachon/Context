"""
MCP Query Understanding Tools (Story 2.6)

Provides query intent classification, enhancement, and history management
via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.search.query_intent import QueryIntentClassifier
from src.search.query_enhancement import QueryEnhancer
from src.search.query_history import QueryHistory

logger = logging.getLogger(__name__)

# Global instances
_classifier = QueryIntentClassifier()
_enhancer = QueryEnhancer()
_history = QueryHistory(max_history=1000)


def register_query_tools(mcp: FastMCP):
    """
    Register query understanding tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def query_classify(query: str) -> Dict[str, Any]:
        """
        Classify query intent and extract context

        Analyzes user query to determine intent (search, understand, refactor,
        debug, optimize, implement, document) and extracts relevant entities
        and keywords.

        Args:
            query: User query string

        Returns:
            Dict with intent, confidence, scope, entities, and keywords
        """
        logger.info(f"MCP query classification invoked: {query[:50]}...")

        try:
            result = _classifier.classify(query)

            return {
                "success": True,
                "query": query,
                "intent": result.intent.value,
                "confidence": result.confidence,
                "scope": {"level": result.scope.level, "target": result.scope.target},
                "entities": result.entities,
                "keywords": result.keywords,
                "context_hints": result.context_hints,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Query classification failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_enhance(
        query: str,
        recent_files: Optional[List[str]] = None,
        project_patterns: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance query with relevant context

        Augments user query with context from recent changes, detected patterns,
        and query intent to improve search accuracy.

        Args:
            query: Original query string
            recent_files: Recently modified files (optional)
            project_patterns: Detected project patterns (optional)

        Returns:
            Dict with enhanced query and context additions
        """
        logger.info(f"MCP query enhancement invoked: {query[:50]}...")

        try:
            intent_result = _classifier.classify(query)
            enhanced = _enhancer.enhance(
                query,
                intent_result,
                recent_files=recent_files,
                project_patterns=project_patterns,
            )

            return {
                "success": True,
                "original_query": enhanced.original_query,
                "enhanced_query": enhanced.enhanced_query,
                "context_additions": enhanced.context_additions,
                "confidence": enhanced.confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Query enhancement failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_followup(query: str) -> Dict[str, Any]:
        """
        Generate follow-up questions to refine query

        Creates clarifying questions based on query intent to help users
        refine their search and get better results.

        Args:
            query: User query string

        Returns:
            Dict with suggested follow-up questions
        """
        logger.info(f"MCP follow-up generation invoked: {query[:50]}...")

        try:
            intent_result = _classifier.classify(query)
            questions = _enhancer.get_follow_up_questions(intent_result)

            return {
                "success": True,
                "query": query,
                "intent": intent_result.intent.value,
                "follow_up_questions": questions,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_history_add(
        query: str, intent: str, results_count: int, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add query to history

        Records a query and its results for future reference and pattern analysis.

        Args:
            query: Query string
            intent: Detected intent
            results_count: Number of results returned
            tags: Optional tags for categorization

        Returns:
            Dict with confirmation and record details
        """
        logger.info(f"MCP history add invoked: {query[:50]}...")

        try:
            record = _history.add_query(query, intent, results_count, tags)

            return {
                "success": True,
                "query": query,
                "timestamp": record.timestamp.isoformat(),
                "total_in_history": len(_history.history),
                "message": "Query added to history",
            }

        except Exception as e:
            logger.error(f"History add failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_history_get(limit: int = 10) -> Dict[str, Any]:
        """
        Get recent queries from history

        Retrieves the most recent queries for quick access and reference.

        Args:
            limit: Maximum number of queries to return (default: 10)

        Returns:
            Dict with list of recent queries
        """
        logger.info(f"MCP history get invoked: limit={limit}")

        try:
            recent = _history.get_recent(limit)

            queries = [
                {
                    "query": r.query,
                    "intent": r.intent,
                    "timestamp": r.timestamp.isoformat(),
                    "results_count": r.results_count,
                    "quality": r.result_quality,
                }
                for r in recent
            ]

            return {
                "success": True,
                "queries": queries,
                "count": len(queries),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"History get failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def query_analytics() -> Dict[str, Any]:
        """
        Get query analytics and statistics

        Provides insights into query patterns, intent distribution, and
        result quality metrics.

        Returns:
            Dict with analytics data
        """
        logger.info("MCP analytics invoked")

        try:
            stats = _history.get_statistics()

            return {
                "success": True,
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Analytics failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
