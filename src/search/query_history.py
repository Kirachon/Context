"""
Query History Service (Story 2.6)

Stores and retrieves query history with results for quick access
and pattern analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


@dataclass
class QueryRecord:
    """Record of a query and its results"""

    query: str
    intent: str
    timestamp: datetime
    results_count: int
    result_quality: float = 0.0  # 0.0-1.0 user rating
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "timestamp": self.timestamp.isoformat(),
            "results_count": self.results_count,
            "result_quality": self.result_quality,
            "tags": self.tags,
            "notes": self.notes,
        }


class QueryHistory:
    """Manages query history storage and retrieval"""

    def __init__(self, max_history: int = 1000):
        """
        Initialize query history

        Args:
            max_history: Maximum number of queries to keep in memory
        """
        self.max_history = max_history
        self.history: List[QueryRecord] = []
        self.history_file: Optional[Path] = None

    def add_query(
        self,
        query: str,
        intent: str,
        results_count: int,
        tags: Optional[List[str]] = None,
    ) -> QueryRecord:
        """
        Add query to history

        Args:
            query: Query string
            intent: Detected intent
            results_count: Number of results returned
            tags: Optional tags for categorization

        Returns:
            QueryRecord
        """
        record = QueryRecord(
            query=query,
            intent=intent,
            timestamp=datetime.now(),
            results_count=results_count,
            tags=tags or [],
        )
        self.history.insert(0, record)

        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[: self.max_history]

        return record

    def rate_query(self, query_index: int, quality: float, notes: str = ""):
        """
        Rate query result quality

        Args:
            query_index: Index in history (0 = most recent)
            quality: Quality rating (0.0-1.0)
            notes: Optional notes about the result
        """
        if 0 <= query_index < len(self.history):
            self.history[query_index].result_quality = max(0.0, min(1.0, quality))
            self.history[query_index].notes = notes

    def get_recent(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent queries"""
        return self.history[:limit]

    def search_history(self, pattern: str) -> List[QueryRecord]:
        """Search query history by pattern"""
        pattern_lower = pattern.lower()
        return [r for r in self.history if pattern_lower in r.query.lower()]

    def get_by_intent(self, intent: str) -> List[QueryRecord]:
        """Get queries by intent"""
        return [r for r in self.history if r.intent == intent]

    def get_by_tag(self, tag: str) -> List[QueryRecord]:
        """Get queries by tag"""
        return [r for r in self.history if tag in r.tags]

    def get_high_quality(self, min_quality: float = 0.7) -> List[QueryRecord]:
        """Get high-quality queries (user-rated)"""
        return [r for r in self.history if r.result_quality >= min_quality]

    def clear_history(self):
        """Clear all history"""
        self.history.clear()

    def save_to_file(self, file_path: Path):
        """Save history to JSON file"""
        self.history_file = file_path
        data = [r.to_dict() for r in self.history]
        file_path.write_text(json.dumps(data, indent=2))

    def load_from_file(self, file_path: Path):
        """Load history from JSON file"""
        self.history_file = file_path
        if not file_path.exists():
            return

        data = json.loads(file_path.read_text())
        self.history.clear()
        for item in data:
            record = QueryRecord(
                query=item["query"],
                intent=item["intent"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                results_count=item["results_count"],
                result_quality=item.get("result_quality", 0.0),
                tags=item.get("tags", []),
                notes=item.get("notes", ""),
            )
            self.history.append(record)

    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics"""
        if not self.history:
            return {}

        intents = {}
        for record in self.history:
            intents[record.intent] = intents.get(record.intent, 0) + 1

        avg_quality = sum(r.result_quality for r in self.history) / len(self.history)
        avg_results = sum(r.results_count for r in self.history) / len(self.history)

        return {
            "total_queries": len(self.history),
            "intent_distribution": intents,
            "average_quality": avg_quality,
            "average_results": avg_results,
            "high_quality_count": len(self.get_high_quality()),
        }


# Module-level stub function for MCP tool integration
def add_to_history(query: str, intent: str, result_count: int) -> Dict:
    """
    Add query to history.

    Stub implementation for MCP tool integration.

    Args:
        query: Query string
        intent: Query intent
        result_count: Number of results

    Returns:
        Dict with status and confirmation
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"QueryHistory stub called with query: {query}, intent: {intent}, result_count: {result_count}")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "add_to_history is a stub implementation",
        "query": query,
        "intent": intent,
        "result_count": result_count,
        "data": {}
    }
