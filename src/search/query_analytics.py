"""
Query Analytics Service (Story 2.6)

Tracks query patterns, frequency, and provides analytics reports
for understanding user search behavior and needs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter


@dataclass
class QueryMetrics:
    """Metrics for a specific query intent"""

    intent: str
    count: int
    avg_results: float
    avg_quality: float
    total_quality_ratings: int


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report"""

    total_queries: int
    time_period: str
    intent_distribution: Dict[str, int]
    intent_metrics: Dict[str, QueryMetrics]
    top_queries: List[tuple]  # (query, count)
    avg_results_per_query: float
    avg_quality_score: float
    high_quality_ratio: float
    generated_at: datetime = field(default_factory=datetime.now)


class QueryAnalytics:
    """Analyzes query patterns and generates reports"""

    def __init__(self):
        """Initialize analytics service"""
        self.query_records: List[Dict[str, Any]] = []

    def add_query_record(
        self,
        query: str,
        intent: str,
        results_count: int,
        quality: float = 0.0,
        tags: Optional[List[str]] = None,
    ):
        """
        Add query record for analytics

        Args:
            query: Query string
            intent: Query intent
            results_count: Number of results returned
            quality: Quality rating (0.0-1.0)
            tags: Optional tags
        """
        record = {
            "query": query,
            "intent": intent,
            "results_count": results_count,
            "quality": quality,
            "tags": tags or [],
            "timestamp": datetime.now(),
        }
        self.query_records.append(record)

    def get_intent_distribution(self) -> Dict[str, int]:
        """Get distribution of queries by intent"""
        intents = [r["intent"] for r in self.query_records]
        return dict(Counter(intents))

    def get_intent_metrics(self) -> Dict[str, QueryMetrics]:
        """Get detailed metrics for each intent"""
        metrics = {}

        for intent in set(r["intent"] for r in self.query_records):
            intent_records = [r for r in self.query_records if r["intent"] == intent]

            count = len(intent_records)
            avg_results = (
                sum(r["results_count"] for r in intent_records) / count
                if count > 0
                else 0
            )

            rated_records = [r for r in intent_records if r["quality"] > 0]
            avg_quality = (
                sum(r["quality"] for r in rated_records) / len(rated_records)
                if rated_records
                else 0
            )

            metrics[intent] = QueryMetrics(
                intent=intent,
                count=count,
                avg_results=avg_results,
                avg_quality=avg_quality,
                total_quality_ratings=len(rated_records),
            )

        return metrics

    def get_top_queries(self, limit: int = 10) -> List[tuple]:
        """Get most frequently queried strings"""
        queries = [r["query"] for r in self.query_records]
        counter = Counter(queries)
        return counter.most_common(limit)

    def get_average_results(self) -> float:
        """Get average number of results per query"""
        if not self.query_records:
            return 0.0
        return sum(r["results_count"] for r in self.query_records) / len(
            self.query_records
        )

    def get_average_quality(self) -> float:
        """Get average quality score"""
        rated = [r for r in self.query_records if r["quality"] > 0]
        if not rated:
            return 0.0
        return sum(r["quality"] for r in rated) / len(rated)

    def get_high_quality_ratio(self, threshold: float = 0.7) -> float:
        """Get ratio of high-quality queries"""
        rated = [r for r in self.query_records if r["quality"] > 0]
        if not rated:
            return 0.0
        high_quality = len([r for r in rated if r["quality"] >= threshold])
        return high_quality / len(rated)

    def get_queries_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get queries with specific tag"""
        return [r for r in self.query_records if tag in r["tags"]]

    def get_queries_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get queries within time range"""
        return [
            r for r in self.query_records if start_time <= r["timestamp"] <= end_time
        ]

    def generate_report(
        self, time_period: str = "all_time", intent_filter: Optional[str] = None
    ) -> AnalyticsReport:
        """
        Generate comprehensive analytics report

        Args:
            time_period: "all_time", "today", "week", "month"
            intent_filter: Optional specific intent to filter by

        Returns:
            AnalyticsReport with all metrics
        """
        # Filter by time period
        records = self._filter_by_time_period(time_period)

        # Filter by intent if specified
        if intent_filter:
            records = [r for r in records if r["intent"] == intent_filter]

        if not records:
            return AnalyticsReport(
                total_queries=0,
                time_period=time_period,
                intent_distribution={},
                intent_metrics={},
                top_queries=[],
                avg_results_per_query=0.0,
                avg_quality_score=0.0,
                high_quality_ratio=0.0,
            )

        # Calculate metrics
        intent_dist = Counter(r["intent"] for r in records)

        intent_metrics = {}
        for intent in intent_dist.keys():
            intent_records = [r for r in records if r["intent"] == intent]
            count = len(intent_records)
            avg_results = sum(r["results_count"] for r in intent_records) / count

            rated = [r for r in intent_records if r["quality"] > 0]
            avg_quality = sum(r["quality"] for r in rated) / len(rated) if rated else 0

            intent_metrics[intent] = QueryMetrics(
                intent=intent,
                count=count,
                avg_results=avg_results,
                avg_quality=avg_quality,
                total_quality_ratings=len(rated),
            )

        top_queries = Counter(r["query"] for r in records).most_common(10)
        avg_results = sum(r["results_count"] for r in records) / len(records)

        rated_records = [r for r in records if r["quality"] > 0]
        avg_quality = (
            sum(r["quality"] for r in rated_records) / len(rated_records)
            if rated_records
            else 0
        )
        high_quality_ratio = (
            len([r for r in rated_records if r["quality"] >= 0.7]) / len(rated_records)
            if rated_records
            else 0
        )

        return AnalyticsReport(
            total_queries=len(records),
            time_period=time_period,
            intent_distribution=dict(intent_dist),
            intent_metrics=intent_metrics,
            top_queries=top_queries,
            avg_results_per_query=avg_results,
            avg_quality_score=avg_quality,
            high_quality_ratio=high_quality_ratio,
        )

    def _filter_by_time_period(self, time_period: str) -> List[Dict[str, Any]]:
        """Filter records by time period"""
        now = datetime.now()

        if time_period == "all_time":
            return self.query_records
        elif time_period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return [r for r in self.query_records if r["timestamp"] >= start]
        elif time_period == "week":
            start = now - timedelta(days=7)
            return [r for r in self.query_records if r["timestamp"] >= start]
        elif time_period == "month":
            start = now - timedelta(days=30)
            return [r for r in self.query_records if r["timestamp"] >= start]
        else:
            return self.query_records

    def clear_records(self):
        """Clear all analytics records"""
        self.query_records.clear()


# Module-level stub function for MCP tool integration
def get_analytics() -> Dict:
    """
    Get query analytics.

    Stub implementation for MCP tool integration.

    Returns:
        Dict with status and analytics data
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("QueryAnalytics stub called")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "get_analytics is a stub implementation",
        "results": [],
        "total_queries": 0,
        "data": {}
    }
