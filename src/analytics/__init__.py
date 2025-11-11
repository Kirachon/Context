"""
Real-Time Analytics Module

Provides comprehensive monitoring and analytics for Context Workspace v2.5.

Components:
- collector: Prometheus metrics collection
- api: REST API for querying analytics
- alerting: Alert management and notifications

Usage:
    from src.analytics import get_metrics_collector, get_alert_manager

    # Record metrics
    collector = get_metrics_collector()
    collector.record_search(latency=0.123, results_count=50, cache_hit=True, cache_layer="l1")

    # Set up alerts
    alert_manager = get_alert_manager()
    alert_manager.add_channel(SlackChannel("https://hooks.slack.com/..."))
"""

from .collector import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
    MetricTimer
)

from .alerting import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    ComparisonOperator,
    NotificationChannel,
    SlackChannel,
    EmailChannel,
    WebhookChannel,
    AnomalyDetector,
    get_alert_manager,
    get_default_alert_rules
)

from .api import (
    router as analytics_router,
    TimeRange,
    Aggregation,
    MetricType,
    AnalyticsDB,
    get_analytics_db
)

__all__ = [
    # Collector
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
    "MetricTimer",

    # Alerting
    "AlertManager",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertStatus",
    "ComparisonOperator",
    "NotificationChannel",
    "SlackChannel",
    "EmailChannel",
    "WebhookChannel",
    "AnomalyDetector",
    "get_alert_manager",
    "get_default_alert_rules",

    # API
    "analytics_router",
    "TimeRange",
    "Aggregation",
    "MetricType",
    "AnalyticsDB",
    "get_analytics_db",
]
