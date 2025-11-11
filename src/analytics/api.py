"""
Real-Time Analytics - REST API

Provides REST endpoints for querying analytics metrics from TimescaleDB.
Supports time ranges, aggregations, and filters for comprehensive analytics.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncpg
import logging

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & MODELS
# ============================================================

class TimeRange(str, Enum):
    """Supported time ranges for queries."""
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"


class Aggregation(str, Enum):
    """Supported aggregation types."""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"
    SUM = "sum"
    COUNT = "count"


class MetricType(str, Enum):
    """Types of metrics available."""
    SEARCH_LATENCY = "search_latency"
    SEARCH_THROUGHPUT = "search_throughput"
    CACHE_HIT_RATE = "cache_hit_rate"
    INDEX_THROUGHPUT = "index_throughput"
    INDEX_ERRORS = "index_errors"
    ACTIVE_USERS = "active_users"
    TOP_FILES = "top_files"
    TOP_QUERIES = "top_queries"


# ============================================================
# DATABASE CONNECTION
# ============================================================

class AnalyticsDB:
    """TimescaleDB connection manager."""

    def __init__(self, connection_string: str):
        """
        Initialize database connection.

        Args:
            connection_string: PostgreSQL/TimescaleDB connection string
        """
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Connected to TimescaleDB analytics database")

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from TimescaleDB")

    async def execute(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Execute query and return results.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single result.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single result row as dictionary or None
        """
        results = await self.execute(query, *args)
        return results[0] if results else None


# Global database instance
_analytics_db: Optional[AnalyticsDB] = None


def get_analytics_db(connection_string: str = None) -> AnalyticsDB:
    """Get or create the global analytics database instance."""
    global _analytics_db
    if _analytics_db is None:
        if not connection_string:
            connection_string = "postgresql://context:password@timescale:5432/context_analytics"
        _analytics_db = AnalyticsDB(connection_string)
    return _analytics_db


# ============================================================
# TIME RANGE HELPERS
# ============================================================

def parse_timerange(timerange: TimeRange) -> str:
    """Convert TimeRange enum to PostgreSQL interval."""
    mapping = {
        TimeRange.ONE_HOUR: "1 hour",
        TimeRange.SIX_HOURS: "6 hours",
        TimeRange.TWENTY_FOUR_HOURS: "24 hours",
        TimeRange.SEVEN_DAYS: "7 days",
        TimeRange.THIRTY_DAYS: "30 days",
    }
    return mapping[timerange]


def get_bucket_size(timerange: TimeRange) -> str:
    """Get appropriate time bucket size for time range."""
    mapping = {
        TimeRange.ONE_HOUR: "1 minute",
        TimeRange.SIX_HOURS: "5 minutes",
        TimeRange.TWENTY_FOUR_HOURS: "15 minutes",
        TimeRange.SEVEN_DAYS: "1 hour",
        TimeRange.THIRTY_DAYS: "6 hours",
    }
    return mapping[timerange]


def get_percentile_value(aggregation: Aggregation) -> float:
    """Get percentile value from aggregation type."""
    mapping = {
        Aggregation.P50: 0.50,
        Aggregation.P95: 0.95,
        Aggregation.P99: 0.99,
    }
    return mapping.get(aggregation, 0.95)


# ============================================================
# API ROUTER
# ============================================================

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/health")
async def health_check():
    """Health check endpoint for analytics API."""
    return {"status": "healthy", "service": "analytics"}


# ============================================================
# SEARCH PERFORMANCE ENDPOINTS
# ============================================================

@router.get("/search-performance")
async def get_search_performance(
    timerange: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for data"),
    aggregation: Aggregation = Query(Aggregation.P95, description="Aggregation type"),
    project_id: Optional[str] = Query(None, description="Filter by project ID")
):
    """
    Get search performance metrics.

    Returns latency, throughput, and cache hit rate over time.

    Example:
        GET /api/v1/analytics/search-performance?timerange=1h&aggregation=p95
    """
    db = get_analytics_db()

    # Build query based on aggregation type
    interval = parse_timerange(timerange)
    bucket_size = get_bucket_size(timerange)

    if aggregation in [Aggregation.P50, Aggregation.P95, Aggregation.P99]:
        percentile = get_percentile_value(aggregation)
        agg_expr = f"percentile_cont({percentile}) WITHIN GROUP (ORDER BY latency)"
    elif aggregation == Aggregation.AVG:
        agg_expr = "AVG(latency)"
    elif aggregation == Aggregation.MAX:
        agg_expr = "MAX(latency)"
    else:
        agg_expr = "AVG(latency)"

    project_filter = "AND project_id = $2" if project_id else ""
    params = [interval] + ([project_id] if project_id else [])

    query = f"""
    SELECT
        time_bucket('{bucket_size}', timestamp) as time_bucket,
        {agg_expr} as latency,
        COUNT(*) as request_count,
        AVG(results_count) as avg_results
    FROM search_metrics
    WHERE timestamp > NOW() - INTERVAL $1 {project_filter}
    GROUP BY time_bucket
    ORDER BY time_bucket
    """

    try:
        datapoints = await db.execute(query, *params)

        # Calculate summary statistics
        if datapoints:
            latencies = [dp["latency"] for dp in datapoints if dp["latency"]]
            summary = {
                aggregation.value: sum(latencies) / len(latencies) if latencies else 0,
                "total_requests": sum(dp["request_count"] for dp in datapoints),
                "avg_results": sum(dp["avg_results"] for dp in datapoints if dp["avg_results"]) / len(datapoints)
            }
        else:
            summary = {aggregation.value: 0, "total_requests": 0, "avg_results": 0}

        return {
            "metric": "search_performance",
            "timerange": timerange,
            "aggregation": aggregation,
            "project_id": project_id,
            "datapoints": datapoints,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error fetching search performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-performance")
async def get_cache_performance(
    timerange: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for data")
):
    """
    Get cache performance metrics including hit rate by layer.

    Example:
        GET /api/v1/analytics/cache-performance?timerange=6h
    """
    db = get_analytics_db()
    interval = parse_timerange(timerange)
    bucket_size = get_bucket_size(timerange)

    query = f"""
    SELECT
        time_bucket('{bucket_size}', timestamp) as time_bucket,
        cache_layer,
        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*)::float * 100 as hit_rate,
        COUNT(*) as total_queries
    FROM search_metrics
    WHERE timestamp > NOW() - INTERVAL $1
    GROUP BY time_bucket, cache_layer
    ORDER BY time_bucket, cache_layer
    """

    try:
        datapoints = await db.execute(query, interval)

        # Calculate overall cache hit rate
        total_hits = sum(dp["hit_rate"] * dp["total_queries"] / 100 for dp in datapoints)
        total_queries = sum(dp["total_queries"] for dp in datapoints)
        overall_hit_rate = (total_hits / total_queries * 100) if total_queries > 0 else 0

        return {
            "metric": "cache_performance",
            "timerange": timerange,
            "overall_hit_rate": overall_hit_rate,
            "datapoints": datapoints
        }

    except Exception as e:
        logger.error(f"Error fetching cache performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# INDEX PERFORMANCE ENDPOINTS
# ============================================================

@router.get("/index-performance")
async def get_index_performance(
    timerange: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for data"),
    project_id: Optional[str] = Query(None, description="Filter by project ID")
):
    """
    Get index performance metrics including throughput and error rate.

    Example:
        GET /api/v1/analytics/index-performance?timerange=24h
    """
    db = get_analytics_db()
    interval = parse_timerange(timerange)
    bucket_size = get_bucket_size(timerange)

    project_filter = "AND project_id = $2" if project_id else ""
    params = [interval] + ([project_id] if project_id else [])

    query = f"""
    SELECT
        time_bucket('{bucket_size}', timestamp) as time_bucket,
        COUNT(*) as files_indexed,
        AVG(duration) as avg_duration,
        SUM(CASE WHEN success THEN 0 ELSE 1 END) as errors,
        COUNT(*) / EXTRACT(EPOCH FROM '{bucket_size}'::interval) as throughput
    FROM index_metrics
    WHERE timestamp > NOW() - INTERVAL $1 {project_filter}
    GROUP BY time_bucket
    ORDER BY time_bucket
    """

    try:
        datapoints = await db.execute(query, *params)

        # Calculate summary
        if datapoints:
            summary = {
                "total_files_indexed": sum(dp["files_indexed"] for dp in datapoints),
                "total_errors": sum(dp["errors"] for dp in datapoints),
                "avg_throughput": sum(dp["throughput"] for dp in datapoints if dp["throughput"]) / len(datapoints),
                "error_rate": sum(dp["errors"] for dp in datapoints) / sum(dp["files_indexed"] for dp in datapoints) * 100
            }
        else:
            summary = {"total_files_indexed": 0, "total_errors": 0, "avg_throughput": 0, "error_rate": 0}

        return {
            "metric": "index_performance",
            "timerange": timerange,
            "project_id": project_id,
            "datapoints": datapoints,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error fetching index performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# USAGE METRICS ENDPOINTS
# ============================================================

@router.get("/usage")
async def get_usage_metrics(
    timerange: TimeRange = Query(TimeRange.TWENTY_FOUR_HOURS, description="Time range for data")
):
    """
    Get usage metrics including active users and query patterns.

    Example:
        GET /api/v1/analytics/usage?timerange=7d
    """
    db = get_analytics_db()
    interval = parse_timerange(timerange)

    # Active users query
    active_users_query = """
    SELECT
        COUNT(DISTINCT user_id) as active_users
    FROM search_metrics
    WHERE timestamp > NOW() - INTERVAL $1
    """

    # Queries per user
    queries_per_user_query = """
    SELECT
        user_id,
        COUNT(*) as query_count
    FROM search_metrics
    WHERE timestamp > NOW() - INTERVAL $1
    GROUP BY user_id
    ORDER BY query_count DESC
    LIMIT 10
    """

    # Top searched files
    top_files_query = """
    SELECT
        file_path,
        project_id,
        COUNT(*) as access_count
    FROM file_access_metrics
    WHERE timestamp > NOW() - INTERVAL $1
    GROUP BY file_path, project_id
    ORDER BY access_count DESC
    LIMIT 20
    """

    try:
        active_users_result = await db.execute_one(active_users_query, interval)
        queries_per_user = await db.execute(queries_per_user_query, interval)
        top_files = await db.execute(top_files_query, interval)

        return {
            "metric": "usage",
            "timerange": timerange,
            "active_users": active_users_result["active_users"] if active_users_result else 0,
            "queries_per_user": queries_per_user,
            "top_files": top_files
        }

    except Exception as e:
        logger.error(f"Error fetching usage metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-queries")
async def get_top_queries(
    timerange: TimeRange = Query(TimeRange.TWENTY_FOUR_HOURS, description="Time range for data"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Get most frequently used query terms.

    Example:
        GET /api/v1/analytics/top-queries?timerange=7d&limit=50
    """
    db = get_analytics_db()
    interval = parse_timerange(timerange)

    query = """
    SELECT
        query_text,
        COUNT(*) as query_count,
        AVG(latency) as avg_latency,
        AVG(results_count) as avg_results
    FROM search_metrics
    WHERE timestamp > NOW() - INTERVAL $1
        AND query_text IS NOT NULL
    GROUP BY query_text
    ORDER BY query_count DESC
    LIMIT $2
    """

    try:
        results = await db.execute(query, interval, limit)

        return {
            "metric": "top_queries",
            "timerange": timerange,
            "queries": results
        }

    except Exception as e:
        logger.error(f"Error fetching top queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# CODE HEALTH ENDPOINTS
# ============================================================

@router.get("/code-health")
async def get_code_health(
    project_id: Optional[str] = Query(None, description="Filter by project ID")
):
    """
    Get code health metrics including dead code and hot spots.

    Example:
        GET /api/v1/analytics/code-health?project_id=frontend
    """
    db = get_analytics_db()

    project_filter = "WHERE project_id = $1" if project_id else ""
    params = [project_id] if project_id else []

    # Dead code (files never accessed in last 30 days)
    dead_code_query = f"""
    SELECT
        project_id,
        COUNT(*) as dead_files,
        (COUNT(*) * 100.0 / NULLIF(total_files, 0)) as dead_code_percentage
    FROM (
        SELECT DISTINCT project_id, file_path
        FROM index_metrics
        {project_filter}
    ) indexed
    LEFT JOIN (
        SELECT DISTINCT file_path
        FROM file_access_metrics
        WHERE timestamp > NOW() - INTERVAL '30 days'
    ) accessed ON indexed.file_path = accessed.file_path
    CROSS JOIN (
        SELECT project_id, COUNT(DISTINCT file_path) as total_files
        FROM index_metrics
        {project_filter}
        GROUP BY project_id
    ) totals
    WHERE accessed.file_path IS NULL
        AND indexed.project_id = totals.project_id
    GROUP BY project_id, total_files
    """

    # Hot spots (files accessed > 10x average)
    hot_spots_query = f"""
    WITH access_stats AS (
        SELECT
            file_path,
            project_id,
            COUNT(*) as access_count
        FROM file_access_metrics
        WHERE timestamp > NOW() - INTERVAL '7 days'
        GROUP BY file_path, project_id
    ),
    avg_access AS (
        SELECT
            project_id,
            AVG(access_count) as avg_count
        FROM access_stats
        GROUP BY project_id
    )
    SELECT
        a.project_id,
        a.file_path,
        a.access_count,
        a.access_count / NULLIF(aa.avg_count, 0) as multiplier
    FROM access_stats a
    JOIN avg_access aa ON a.project_id = aa.project_id
    WHERE a.access_count > aa.avg_count * 10
        {('AND a.project_id = $1' if project_id else '')}
    ORDER BY a.access_count DESC
    LIMIT 20
    """

    try:
        dead_code = await db.execute(dead_code_query, *params)
        hot_spots = await db.execute(hot_spots_query, *params)

        return {
            "metric": "code_health",
            "project_id": project_id,
            "dead_code": dead_code,
            "hot_spots": hot_spots
        }

    except Exception as e:
        logger.error(f"Error fetching code health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# EXPORT ENDPOINT
# ============================================================

@router.get("/export")
async def export_metrics(
    metric: MetricType = Query(..., description="Metric type to export"),
    timerange: TimeRange = Query(TimeRange.TWENTY_FOUR_HOURS, description="Time range"),
    format: str = Query("json", regex="^(json|csv)$", description="Export format")
):
    """
    Export metrics in JSON or CSV format for external analysis.

    Example:
        GET /api/v1/analytics/export?metric=search_latency&timerange=7d&format=csv
    """
    # This would call the appropriate endpoint and format the data
    # For now, return a placeholder
    return {
        "message": "Export functionality - implementation placeholder",
        "metric": metric,
        "timerange": timerange,
        "format": format
    }
