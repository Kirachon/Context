# Real-Time Analytics Dashboard System

## Overview

The Context Workspace v2.5 Real-Time Analytics Dashboard System provides comprehensive monitoring, metrics collection, and alerting capabilities for the Context platform. It consists of:

1. **Prometheus Metrics Collector** - Collects and exports metrics
2. **TimescaleDB** - Time-series database for historical data
3. **Grafana Dashboards** - Visualization and monitoring
4. **Analytics REST API** - Query metrics programmatically
5. **Alerting System** - Threshold-based alerts and anomaly detection

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Context Application                   │
│  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Metrics Collector│  │   Alerting System        │   │
│  │ (Prometheus)     │  │   (Threshold Detection)  │   │
│  └────────┬─────────┘  └──────────┬───────────────┘   │
└───────────┼────────────────────────┼───────────────────┘
            │                        │
            ▼                        ▼
┌───────────────────────┐  ┌────────────────────────────┐
│    Prometheus         │  │      AlertManager          │
│    (Scraping)         │  │      (Notifications)       │
└───────┬───────────────┘  └────────────────────────────┘
        │
        ▼
┌───────────────────────┐  ┌────────────────────────────┐
│    TimescaleDB        │  │       Grafana              │
│    (Time-Series)      │  │       (Visualization)      │
└───────────────────────┘  └────────────────────────────┘
```

## Quick Start

### 1. Start the Services

```bash
cd /home/user/Context/deployment/docker
docker-compose up -d
```

This starts:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **TimescaleDB**: localhost:5433
- **AlertManager**: http://localhost:9093

### 2. Access Dashboards

Open Grafana at http://localhost:3000 and navigate to:

- **Search Performance** - Latency, throughput, cache hit rate
- **Index Performance** - Files/sec, queue size, errors
- **Usage Patterns** - Active users, top files, query patterns
- **Code Health** - Dead code, hot spots, coverage
- **System Resources** - CPU, memory, disk, network

### 3. Use Analytics API

Query metrics programmatically:

```bash
# Get search performance metrics
curl http://localhost:8000/api/v1/analytics/search-performance?timerange=1h&aggregation=p95

# Get cache performance
curl http://localhost:8000/api/v1/analytics/cache-performance?timerange=6h

# Get usage metrics
curl http://localhost:8000/api/v1/analytics/usage?timerange=24h

# Get code health
curl http://localhost:8000/api/v1/analytics/code-health?project_id=frontend
```

## Components

### 1. Metrics Collector (`src/analytics/collector.py`)

Collects and exports metrics to Prometheus.

**Usage in Code:**

```python
from src.analytics import get_metrics_collector

collector = get_metrics_collector()

# Record search metrics
collector.record_search(
    latency=0.123,
    results_count=50,
    project_id="frontend",
    cache_hit=True,
    cache_layer="l1",
    status="success"
)

# Record index metrics
collector.record_index(
    duration=1.5,
    project_id="backend",
    file_type="py",
    success=True
)

# Update gauges
collector.update_index_queue(size=1500, project_id="backend")
collector.update_active_users(count=25, time_window="5m")

# Use timer context manager
from src.analytics import MetricTimer

with MetricTimer("search", collector):
    # Perform search operation
    results = search_engine.search(query)
```

**Metrics Collected:**

| Category | Metric | Type | Description |
|----------|--------|------|-------------|
| **Search** | `search_latency_seconds` | Histogram | Query latency distribution |
| | `search_requests_total` | Counter | Total search requests |
| | `cache_hits_total` | Counter | Cache hits by layer |
| | `cache_misses_total` | Counter | Cache misses |
| **Index** | `files_indexed_total` | Counter | Files successfully indexed |
| | `index_errors_total` | Counter | Indexing errors |
| | `index_queue_size` | Gauge | Current queue size |
| | `index_throughput_files_per_second` | Gauge | Files indexed per second |
| **Usage** | `active_users` | Gauge | Active users by time window |
| | `file_access_total` | Counter | File access count |
| | `query_terms_total` | Counter | Query term frequency |
| **Code Health** | `dead_code_percentage` | Gauge | Dead code percentage |
| | `hot_spots_count` | Gauge | Hot spot file count |
| | `index_coverage_percentage` | Gauge | Index coverage |

### 2. TimescaleDB Schema

Hypertables with automatic partitioning, continuous aggregates, and retention policies.

**Tables:**

- `search_metrics` - Search performance data (7 day retention)
- `index_metrics` - Indexing performance data (7 day retention)
- `file_access_metrics` - File access patterns (30 day retention)

**Continuous Aggregates:**

- `search_metrics_hourly` - Hourly rollups (90 day retention)
- `search_metrics_daily` - Daily rollups (365 day retention)
- `index_metrics_hourly` - Hourly index rollups (90 day retention)

**Automatic Compression:**

Data older than 3 days is automatically compressed to save storage.

### 3. Analytics REST API (`src/analytics/api.py`)

Query metrics via REST endpoints.

**Endpoints:**

```
GET /api/v1/analytics/health
GET /api/v1/analytics/search-performance
GET /api/v1/analytics/cache-performance
GET /api/v1/analytics/index-performance
GET /api/v1/analytics/usage
GET /api/v1/analytics/top-queries
GET /api/v1/analytics/code-health
GET /api/v1/analytics/export
```

**Example:**

```python
# Use the analytics API
from src.analytics import analytics_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(analytics_router)
```

### 4. Alerting System (`src/analytics/alerting.py`)

Threshold-based alerts and anomaly detection with multiple notification channels.

**Usage:**

```python
from src.analytics.alerting import (
    get_alert_manager,
    AlertRule,
    AlertSeverity,
    ComparisonOperator,
    SlackChannel
)

# Get alert manager
alert_manager = get_alert_manager()

# Add notification channel
slack = SlackChannel(webhook_url="https://hooks.slack.com/services/...")
alert_manager.add_channel(slack)

# Add custom alert rule
alert_manager.add_rule(AlertRule(
    name="custom_high_latency",
    metric="search_latency_p95",
    threshold=0.3,  # 300ms
    operator=ComparisonOperator.GREATER_THAN,
    severity=AlertSeverity.WARNING,
    description="Custom: Search latency exceeds 300ms"
))

# Evaluate metrics
await alert_manager.evaluate({
    "search_latency_p95": 0.45,
    "cache_hit_rate": 0.35,
    "index_queue_size": 15000
})

# Get active alerts
active_alerts = alert_manager.get_active_alerts()

# Acknowledge an alert
alert_manager.acknowledge_alert(alert_id="...", acknowledged_by="user@example.com")
```

**Default Alert Rules:**

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Search Latency | p95 > 500ms for 5min | Warning |
| Critical Search Latency | p99 > 2s for 5min | Critical |
| Low Cache Hit Rate | < 40% for 10min | Warning |
| High Search Error Rate | > 5% for 5min | Error |
| High Index Error Rate | > 5% for 10min | Error |
| Large Index Queue | > 10,000 files for 15min | Warning |
| High Memory Usage | > 2GB for 5min | Warning |
| Critical Memory Usage | > 4GB for 5min | Critical |
| High CPU Usage | > 85% for 10min | Warning |

**Notification Channels:**

- **Slack** - Webhook integration
- **Email** - SMTP notifications
- **Webhook** - Custom HTTP webhooks

### 5. Grafana Dashboards

Pre-configured dashboards for comprehensive monitoring.

**Dashboards:**

1. **Search Performance** (`search-performance.json`)
   - Search latency (p50, p95, p99)
   - Throughput and request rate
   - Cache hit rate by layer
   - Error rate and distribution

2. **Index Performance** (`index-performance.json`)
   - Index throughput
   - Queue size trends
   - Error rate by type
   - Duration by file type

3. **Usage Patterns** (`usage-patterns.json`)
   - Active users (5m, 1h, 24h)
   - Most searched files
   - Top query terms
   - Activity heatmaps

4. **Code Health** (`code-health.json`)
   - Dead code percentage
   - Index coverage
   - Hot spot files
   - Code health score

5. **System Resources** (`system-resources.json`)
   - CPU and memory usage
   - File descriptors
   - Network I/O
   - Garbage collection

## Configuration

### Environment Variables

```bash
# TimescaleDB
TIMESCALE_DB=context_analytics
TIMESCALE_USER=context
TIMESCALE_PASSWORD=password

# Grafana
GF_SECURITY_ADMIN_PASSWORD=admin

# Alerting
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
ALERT_EMAIL=alerts@example.com
```

### Customizing Alert Rules

Edit `/home/user/Context/deployment/docker/alert_rules.yml`:

```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: CustomMetricAlert
        expr: your_metric > threshold
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Custom alert fired"
          description: "Your metric exceeded threshold"
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

## Performance Requirements

- **Dashboard Load Time**: < 2 seconds
- **Real-Time Updates**: Every 5 seconds
- **Data Retention**: 7 days (raw), 90 days (hourly aggregates), 365 days (daily aggregates)
- **Query Latency**: < 1 second for most queries
- **Storage**: ~10MB per million events (compressed)

## Troubleshooting

### Dashboard Not Loading

1. Check if services are running:
   ```bash
   docker-compose ps
   ```

2. Check Prometheus targets:
   ```
   http://localhost:9090/targets
   ```

3. Verify metrics are being collected:
   ```
   http://localhost:9090/graph?g0.expr=search_requests_total
   ```

### No Data in TimescaleDB

1. Check database connection:
   ```bash
   docker exec -it context-timescale psql -U context -d context_analytics -c "SELECT COUNT(*) FROM search_metrics;"
   ```

2. Verify initialization script ran:
   ```bash
   docker logs context-timescale | grep "TimescaleDB analytics database initialized"
   ```

### Alerts Not Firing

1. Check alert rules are loaded in Prometheus:
   ```
   http://localhost:9090/alerts
   ```

2. Check AlertManager is receiving alerts:
   ```
   http://localhost:9093/#/alerts
   ```

3. Verify notification channels are configured in AlertManager config

## Exporting Data

### Export to CSV

```bash
# Via Analytics API
curl "http://localhost:8000/api/v1/analytics/export?metric=search_latency&timerange=7d&format=csv" > metrics.csv
```

### Export from TimescaleDB

```bash
# Connect to database
docker exec -it context-timescale psql -U context -d context_analytics

# Export query results
\copy (SELECT * FROM search_metrics WHERE timestamp > NOW() - INTERVAL '7 days') TO '/tmp/search_metrics.csv' CSV HEADER;
```

### Export Grafana Dashboards

```bash
# Export dashboard JSON
curl http://localhost:3000/api/dashboards/uid/search-performance > dashboard_backup.json
```

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI, Request
from src.analytics import get_metrics_collector
import time

app = FastAPI()
collector = get_metrics_collector()

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    # Record metrics
    collector.record_api_request_size(
        size_bytes=request.headers.get("content-length", 0),
        endpoint=request.url.path
    )
    collector.record_api_response_size(
        size_bytes=len(response.body),
        endpoint=request.url.path
    )

    return response
```

### Search Service Integration

```python
from src.analytics import get_metrics_collector

class SearchService:
    def __init__(self):
        self.collector = get_metrics_collector()

    async def search(self, query: str, project_id: str):
        start = time.time()

        try:
            # Check cache
            cached = await self.cache.get(query)
            if cached:
                latency = time.time() - start
                self.collector.record_search(
                    latency=latency,
                    results_count=len(cached),
                    project_id=project_id,
                    cache_hit=True,
                    cache_layer="l1"
                )
                return cached

            # Perform search
            results = await self.engine.search(query)

            # Record metrics
            latency = time.time() - start
            self.collector.record_search(
                latency=latency,
                results_count=len(results),
                project_id=project_id,
                cache_hit=False,
                status="success"
            )

            return results

        except Exception as e:
            latency = time.time() - start
            self.collector.record_search(
                latency=latency,
                results_count=0,
                project_id=project_id,
                cache_hit=False,
                status="error"
            )
            raise
```

## Best Practices

1. **Metric Naming**: Use descriptive names with units (e.g., `_seconds`, `_bytes`, `_total`)
2. **Labels**: Keep cardinality low (< 100 unique values per label)
3. **Aggregation**: Use continuous aggregates for long-term queries
4. **Retention**: Archive data before deletion if needed for compliance
5. **Alerting**: Set appropriate thresholds and cooldown periods
6. **Dashboards**: Keep dashboards focused (5-10 panels max)

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Context Workspace v2.5 PRD](/home/user/Context/WORKSPACE_V2.5_PRD.md)
- [Context Workspace v2.5 Architecture](/home/user/Context/WORKSPACE_V2.5_ARCHITECTURE.md)

## Support

For issues or questions:
1. Check Grafana dashboards for system health
2. Review Prometheus alerts
3. Check logs: `docker logs context-server`
4. Review TimescaleDB data: `docker exec -it context-timescale psql -U context -d context_analytics`
