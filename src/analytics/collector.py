"""
Real-Time Analytics - Metrics Collector

Collects and exports metrics to Prometheus for real-time monitoring.
Supports search performance, index performance, usage, and code health metrics.
"""

from typing import Optional, Dict, Any
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
import time
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and exports metrics to Prometheus.

    Metrics Categories:
    1. Search Performance: Latency, throughput, cache hit rate
    2. Index Performance: Files/sec, queue size, errors
    3. Usage Metrics: Active users, queries/user, top files
    4. Code Health: Dead code, hot spots, coverage
    5. System Resources: CPU, memory, disk, network
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.

        Args:
            registry: Prometheus registry (None uses default global registry)
        """
        self.registry = registry

        # ============================================================
        # SEARCH PERFORMANCE METRICS
        # ============================================================

        self.search_latency = Histogram(
            "search_latency_seconds",
            "Search query latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry
        )

        self.search_requests = Counter(
            "search_requests_total",
            "Total number of search requests",
            labelnames=["project_id", "status"],
            registry=registry
        )

        self.cache_hits = Counter(
            "cache_hits_total",
            "Total cache hits by layer",
            labelnames=["layer"],  # l1, l2, l3
            registry=registry
        )

        self.cache_misses = Counter(
            "cache_misses_total",
            "Total cache misses",
            registry=registry
        )

        self.search_results = Summary(
            "search_results_count",
            "Number of results returned per search",
            registry=registry
        )

        # ============================================================
        # INDEX PERFORMANCE METRICS
        # ============================================================

        self.files_indexed = Counter(
            "files_indexed_total",
            "Total files successfully indexed",
            labelnames=["project_id", "file_type"],
            registry=registry
        )

        self.index_errors = Counter(
            "index_errors_total",
            "Total indexing errors",
            labelnames=["project_id", "error_type"],
            registry=registry
        )

        self.index_queue_size = Gauge(
            "index_queue_size",
            "Current size of indexing queue",
            labelnames=["project_id"],
            registry=registry
        )

        self.index_duration = Histogram(
            "index_duration_seconds",
            "Time taken to index a file in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            labelnames=["file_type"],
            registry=registry
        )

        self.index_throughput = Gauge(
            "index_throughput_files_per_second",
            "Files indexed per second",
            labelnames=["project_id"],
            registry=registry
        )

        # ============================================================
        # USAGE METRICS
        # ============================================================

        self.active_users = Gauge(
            "active_users",
            "Number of active users",
            labelnames=["time_window"],  # 5m, 1h, 24h
            registry=registry
        )

        self.queries_per_user = Summary(
            "queries_per_user",
            "Number of queries per user",
            registry=registry
        )

        self.file_access_count = Counter(
            "file_access_total",
            "Number of times a file was accessed in search results",
            labelnames=["project_id", "file_path"],
            registry=registry
        )

        self.query_terms = Counter(
            "query_terms_total",
            "Most frequently used query terms",
            labelnames=["term"],
            registry=registry
        )

        # ============================================================
        # CODE HEALTH METRICS
        # ============================================================

        self.dead_code_percentage = Gauge(
            "dead_code_percentage",
            "Percentage of code never searched (dead code)",
            labelnames=["project_id"],
            registry=registry
        )

        self.hot_spots = Gauge(
            "hot_spots_count",
            "Number of hot spot files (frequently accessed)",
            labelnames=["project_id", "threshold"],
            registry=registry
        )

        self.index_coverage = Gauge(
            "index_coverage_percentage",
            "Percentage of files indexed vs total files",
            labelnames=["project_id"],
            registry=registry
        )

        self.code_duplication = Gauge(
            "code_duplication_percentage",
            "Percentage of duplicated code detected",
            labelnames=["project_id"],
            registry=registry
        )

        # ============================================================
        # SYSTEM RESOURCE METRICS (supplementary to process metrics)
        # ============================================================

        self.vector_db_size = Gauge(
            "vector_db_size_bytes",
            "Size of vector database in bytes",
            registry=registry
        )

        self.embedding_cache_size = Gauge(
            "embedding_cache_size_bytes",
            "Size of embedding cache in bytes",
            registry=registry
        )

        self.api_request_size = Summary(
            "api_request_size_bytes",
            "Size of API requests in bytes",
            labelnames=["endpoint"],
            registry=registry
        )

        self.api_response_size = Summary(
            "api_response_size_bytes",
            "Size of API responses in bytes",
            labelnames=["endpoint"],
            registry=registry
        )

    # ============================================================
    # SEARCH PERFORMANCE RECORDING
    # ============================================================

    def record_search(
        self,
        latency: float,
        results_count: int,
        project_id: str = "default",
        cache_hit: bool = False,
        cache_layer: Optional[str] = None,
        status: str = "success"
    ):
        """
        Record search metrics.

        Args:
            latency: Query latency in seconds
            results_count: Number of results returned
            project_id: Project identifier
            cache_hit: Whether result was from cache
            cache_layer: Cache layer (l1, l2, l3)
            status: Request status (success, error, timeout)
        """
        self.search_latency.observe(latency)
        self.search_requests.labels(project_id=project_id, status=status).inc()
        self.search_results.observe(results_count)

        if cache_hit and cache_layer:
            self.cache_hits.labels(layer=cache_layer).inc()
        elif not cache_hit:
            self.cache_misses.inc()

    def record_cache_hit(self, layer: str):
        """Record a cache hit for a specific layer."""
        self.cache_hits.labels(layer=layer).inc()

    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses.inc()

    # ============================================================
    # INDEX PERFORMANCE RECORDING
    # ============================================================

    def record_index(
        self,
        duration: float,
        project_id: str,
        file_type: str,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        Record indexing metrics.

        Args:
            duration: Time taken to index in seconds
            project_id: Project identifier
            file_type: Type of file (py, js, md, etc.)
            success: Whether indexing succeeded
            error_type: Type of error if failed (parsing, memory, timeout)
        """
        if success:
            self.files_indexed.labels(
                project_id=project_id,
                file_type=file_type
            ).inc()
            self.index_duration.labels(file_type=file_type).observe(duration)
        else:
            self.index_errors.labels(
                project_id=project_id,
                error_type=error_type or "unknown"
            ).inc()

    def update_index_queue(self, size: int, project_id: str = "default"):
        """Update the indexing queue size."""
        self.index_queue_size.labels(project_id=project_id).set(size)

    def update_index_throughput(self, files_per_second: float, project_id: str = "default"):
        """Update indexing throughput (files per second)."""
        self.index_throughput.labels(project_id=project_id).set(files_per_second)

    # ============================================================
    # USAGE METRICS RECORDING
    # ============================================================

    def update_active_users(self, count: int, time_window: str = "5m"):
        """
        Update active users count.

        Args:
            count: Number of active users
            time_window: Time window (5m, 1h, 24h)
        """
        self.active_users.labels(time_window=time_window).set(count)

    def record_user_query(self, query_count: int):
        """Record number of queries for a user."""
        self.queries_per_user.observe(query_count)

    def record_file_access(self, project_id: str, file_path: str):
        """Record a file being accessed in search results."""
        self.file_access_count.labels(
            project_id=project_id,
            file_path=file_path
        ).inc()

    def record_query_term(self, term: str):
        """Record a query term for frequency analysis."""
        self.query_terms.labels(term=term).inc()

    # ============================================================
    # CODE HEALTH METRICS RECORDING
    # ============================================================

    def update_dead_code_percentage(self, percentage: float, project_id: str):
        """Update dead code percentage (files never searched)."""
        self.dead_code_percentage.labels(project_id=project_id).set(percentage)

    def update_hot_spots(self, count: int, project_id: str, threshold: str = "10x"):
        """
        Update hot spots count.

        Args:
            count: Number of hot spot files
            project_id: Project identifier
            threshold: Access frequency threshold (5x, 10x, 20x average)
        """
        self.hot_spots.labels(project_id=project_id, threshold=threshold).set(count)

    def update_index_coverage(self, percentage: float, project_id: str):
        """Update index coverage percentage."""
        self.index_coverage.labels(project_id=project_id).set(percentage)

    def update_code_duplication(self, percentage: float, project_id: str):
        """Update code duplication percentage."""
        self.code_duplication.labels(project_id=project_id).set(percentage)

    # ============================================================
    # SYSTEM RESOURCE METRICS RECORDING
    # ============================================================

    def update_vector_db_size(self, size_bytes: int):
        """Update vector database size in bytes."""
        self.vector_db_size.set(size_bytes)

    def update_embedding_cache_size(self, size_bytes: int):
        """Update embedding cache size in bytes."""
        self.embedding_cache_size.set(size_bytes)

    def record_api_request_size(self, size_bytes: int, endpoint: str):
        """Record API request size."""
        self.api_request_size.labels(endpoint=endpoint).observe(size_bytes)

    def record_api_response_size(self, size_bytes: int, endpoint: str):
        """Record API response size."""
        self.api_response_size.labels(endpoint=endpoint).observe(size_bytes)

    # ============================================================
    # EXPORT METHODS
    # ============================================================

    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST


# Global singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector():
    """Reset the global metrics collector (mainly for testing)."""
    global _metrics_collector
    _metrics_collector = None


# Context manager for timing operations
class MetricTimer:
    """Context manager for timing operations and recording to Prometheus."""

    def __init__(self, metric_name: str, collector: Optional[MetricsCollector] = None):
        """
        Initialize timer.

        Args:
            metric_name: Name of the metric to record
            collector: Metrics collector instance
        """
        self.metric_name = metric_name
        self.collector = collector or get_metrics_collector()
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        duration = time.time() - self.start_time

        # Record based on metric name
        if self.metric_name == "search":
            self.collector.search_latency.observe(duration)
        elif self.metric_name.startswith("index_"):
            file_type = self.metric_name.split("_", 1)[1]
            self.collector.index_duration.labels(file_type=file_type).observe(duration)
