"""
Example Integration - Real-Time Analytics System

This example demonstrates how to integrate the analytics system into the Context application.
"""

import asyncio
import time
from typing import List
from datetime import datetime

from src.analytics import (
    get_metrics_collector,
    get_alert_manager,
    AlertRule,
    AlertSeverity,
    ComparisonOperator,
    SlackChannel,
    MetricTimer
)


# ============================================================
# EXAMPLE 1: Basic Metrics Collection
# ============================================================

def example_basic_metrics():
    """Example: Collect basic metrics."""
    print("Example 1: Basic Metrics Collection\n")

    collector = get_metrics_collector()

    # Record a successful search
    collector.record_search(
        latency=0.123,
        results_count=50,
        project_id="frontend",
        cache_hit=True,
        cache_layer="l1",
        status="success"
    )
    print("✓ Recorded search metric (123ms, cache hit)")

    # Record a cache miss
    collector.record_search(
        latency=0.456,
        results_count=30,
        project_id="backend",
        cache_hit=False,
        status="success"
    )
    print("✓ Recorded search metric (456ms, cache miss)")

    # Record indexing metrics
    collector.record_index(
        duration=1.5,
        project_id="frontend",
        file_type="tsx",
        success=True
    )
    print("✓ Recorded index metric (1.5s, TSX file)")

    # Record an indexing error
    collector.record_index(
        duration=0.5,
        project_id="backend",
        file_type="py",
        success=False,
        error_type="parsing_error"
    )
    print("✓ Recorded index error (parsing error)")

    # Update gauges
    collector.update_index_queue(size=1500, project_id="backend")
    collector.update_active_users(count=25, time_window="5m")
    print("✓ Updated gauges (queue: 1500, users: 25)")

    print("\n" + "="*60 + "\n")


# ============================================================
# EXAMPLE 2: Using Context Manager for Timing
# ============================================================

def example_timing_context_manager():
    """Example: Use context manager for automatic timing."""
    print("Example 2: Timing Context Manager\n")

    collector = get_metrics_collector()

    # Time a search operation
    with MetricTimer("search", collector):
        # Simulate search operation
        time.sleep(0.1)
        results = ["result1", "result2", "result3"]

    print("✓ Search operation timed automatically (100ms)")

    # Time an indexing operation
    with MetricTimer("index_py", collector):
        # Simulate indexing a Python file
        time.sleep(0.5)

    print("✓ Index operation timed automatically (500ms)")

    print("\n" + "="*60 + "\n")


# ============================================================
# EXAMPLE 3: Real-World Search Integration
# ============================================================

class SearchService:
    """Example search service with integrated metrics."""

    def __init__(self):
        self.collector = get_metrics_collector()
        self.cache = {}  # Simple cache

    async def search(self, query: str, project_id: str) -> List[str]:
        """
        Perform search with integrated metrics collection.

        Args:
            query: Search query
            project_id: Project identifier

        Returns:
            List of search results
        """
        start = time.time()

        try:
            # Check L1 cache
            cache_key = f"{project_id}:{query}"
            if cache_key in self.cache:
                results = self.cache[cache_key]
                latency = time.time() - start

                self.collector.record_search(
                    latency=latency,
                    results_count=len(results),
                    project_id=project_id,
                    cache_hit=True,
                    cache_layer="l1",
                    status="success"
                )

                return results

            # Simulate search operation
            await asyncio.sleep(0.2)  # Simulate database query
            results = [f"result_{i}" for i in range(10)]

            # Cache results
            self.cache[cache_key] = results

            # Record metrics
            latency = time.time() - start
            self.collector.record_search(
                latency=latency,
                results_count=len(results),
                project_id=project_id,
                cache_hit=False,
                status="success"
            )

            # Record file access for each result
            for result in results[:3]:  # Top 3 results
                self.collector.record_file_access(
                    project_id=project_id,
                    file_path=f"/path/to/{result}.py"
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


async def example_search_integration():
    """Example: Real-world search service integration."""
    print("Example 3: Search Service Integration\n")

    search_service = SearchService()

    # First search (cache miss)
    results = await search_service.search("authentication", "frontend")
    print(f"✓ First search: {len(results)} results (cache miss)")

    # Second search (cache hit)
    results = await search_service.search("authentication", "frontend")
    print(f"✓ Second search: {len(results)} results (cache hit)")

    # Different project
    results = await search_service.search("database", "backend")
    print(f"✓ Third search: {len(results)} results (cache miss)")

    print("\n" + "="*60 + "\n")


# ============================================================
# EXAMPLE 4: Alert Management
# ============================================================

async def example_alert_management():
    """Example: Set up and manage alerts."""
    print("Example 4: Alert Management\n")

    alert_manager = get_alert_manager()

    # Add a custom alert rule
    custom_rule = AlertRule(
        name="demo_high_latency",
        metric="search_latency_p95",
        threshold=0.3,  # 300ms
        operator=ComparisonOperator.GREATER_THAN,
        severity=AlertSeverity.WARNING,
        description="Demo: Search latency exceeds 300ms"
    )
    alert_manager.add_rule(custom_rule)
    print("✓ Added custom alert rule")

    # Add notification channel (demo only - not actually sending)
    # In production, use real webhook URL
    slack_channel = SlackChannel(webhook_url="https://hooks.slack.com/demo")
    alert_manager.add_channel(slack_channel)
    print("✓ Added Slack notification channel")

    # Simulate metrics evaluation
    print("\nSimulating metrics evaluation:")

    # Scenario 1: Normal metrics (no alerts)
    print("  - Evaluating normal metrics...")
    await alert_manager.evaluate({
        "search_latency_p95": 0.15,  # 150ms - OK
        "cache_hit_rate": 0.65,      # 65% - OK
        "index_queue_size": 500      # 500 - OK
    })
    print("    ✓ No alerts triggered")

    # Scenario 2: High latency (alert triggered)
    print("  - Evaluating high latency metrics...")
    await alert_manager.evaluate({
        "search_latency_p95": 0.55,  # 550ms - ALERT!
        "cache_hit_rate": 0.65,
        "index_queue_size": 500
    })
    active_alerts = alert_manager.get_active_alerts()
    print(f"    ✓ {len(active_alerts)} alert(s) triggered")

    # List active alerts
    if active_alerts:
        print("\n  Active Alerts:")
        for alert in active_alerts:
            print(f"    - {alert.rule_name}: {alert.message}")

    print("\n" + "="*60 + "\n")


# ============================================================
# EXAMPLE 5: Code Health Metrics
# ============================================================

def example_code_health_metrics():
    """Example: Track code health metrics."""
    print("Example 5: Code Health Metrics\n")

    collector = get_metrics_collector()

    # Update dead code percentage
    collector.update_dead_code_percentage(
        percentage=15.5,
        project_id="frontend"
    )
    print("✓ Updated dead code: 15.5% (frontend)")

    # Update index coverage
    collector.update_index_coverage(
        percentage=92.3,
        project_id="frontend"
    )
    print("✓ Updated index coverage: 92.3% (frontend)")

    # Update hot spots
    collector.update_hot_spots(
        count=8,
        project_id="backend",
        threshold="10x"
    )
    print("✓ Updated hot spots: 8 files (backend)")

    # Update code duplication
    collector.update_code_duplication(
        percentage=8.2,
        project_id="backend"
    )
    print("✓ Updated code duplication: 8.2% (backend)")

    print("\n" + "="*60 + "\n")


# ============================================================
# EXAMPLE 6: Bulk Operations
# ============================================================

async def example_bulk_operations():
    """Example: Simulate bulk operations with metrics."""
    print("Example 6: Bulk Operations\n")

    collector = get_metrics_collector()

    # Simulate batch indexing
    print("Simulating batch indexing of 100 files...")

    indexed_count = 0
    error_count = 0

    for i in range(100):
        file_type = ["py", "js", "ts", "md"][i % 4]
        duration = 0.1 + (i % 10) * 0.1
        success = i % 20 != 0  # 5% error rate

        collector.record_index(
            duration=duration,
            project_id="backend",
            file_type=file_type,
            success=success,
            error_type="timeout" if not success else None
        )

        if success:
            indexed_count += 1
        else:
            error_count += 1

        # Update queue size
        remaining = 100 - (i + 1)
        collector.update_index_queue(size=remaining, project_id="backend")

    print(f"✓ Indexed {indexed_count} files")
    print(f"✗ {error_count} errors")
    print(f"✓ Queue cleared")

    # Simulate search load
    print("\nSimulating 50 concurrent searches...")

    search_service = SearchService()
    tasks = []

    for i in range(50):
        query = f"query_{i % 10}"
        project = ["frontend", "backend"][i % 2]
        tasks.append(search_service.search(query, project))

    await asyncio.gather(*tasks)
    print("✓ Completed 50 searches")

    print("\n" + "="*60 + "\n")


# ============================================================
# MAIN DEMO
# ============================================================

async def run_all_examples():
    """Run all examples."""
    print("\n" + "="*60)
    print("Real-Time Analytics System - Integration Examples")
    print("="*60 + "\n")

    # Run examples
    example_basic_metrics()
    example_timing_context_manager()
    await example_search_integration()
    await example_alert_management()
    example_code_health_metrics()
    await example_bulk_operations()

    print("="*60)
    print("All examples completed successfully!")
    print("="*60 + "\n")

    print("Next Steps:")
    print("1. View metrics in Prometheus: http://localhost:9090")
    print("2. View dashboards in Grafana: http://localhost:3000")
    print("3. Query analytics API: http://localhost:8000/api/v1/analytics/health")
    print("4. Check alerts: http://localhost:9093")
    print()


if __name__ == "__main__":
    asyncio.run(run_all_examples())
