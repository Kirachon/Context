"""
Real-Time Analytics - Alerting System

Provides threshold-based alerts and anomaly detection for monitoring.
Supports multiple notification channels (Slack, email, webhook).
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & MODELS
# ============================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ComparisonOperator(str, Enum):
    """Comparison operators for threshold rules."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="


@dataclass
class AlertRule:
    """
    Definition of an alert rule.

    Example:
        AlertRule(
            name="high_search_latency",
            metric="search_latency_p95",
            threshold=0.5,  # 500ms
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.WARNING,
            evaluation_window="5m"
        )
    """
    name: str
    metric: str
    threshold: float
    operator: ComparisonOperator
    severity: AlertSeverity
    evaluation_window: str = "5m"  # Time window for evaluation
    description: Optional[str] = None
    enabled: bool = True
    cooldown_period: int = 300  # Seconds before re-alerting


@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    alert_id: Optional[str] = None

    def __post_init__(self):
        """Generate alert ID if not provided."""
        if not self.alert_id:
            self.alert_id = f"{self.rule_name}_{self.timestamp.isoformat()}"


# ============================================================
# NOTIFICATION CHANNELS
# ============================================================

class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send alert notification.

        Args:
            alert: Alert to send

        Returns:
            True if successful, False otherwise
        """
        pass


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    def __init__(self, webhook_url: str):
        """
        Initialize Slack channel.

        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            # Color based on severity
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9900",
                AlertSeverity.ERROR: "#ff0000",
                AlertSeverity.CRITICAL: "#8b0000",
            }

            payload = {
                "attachments": [
                    {
                        "fallback": alert.message,
                        "color": color_map[alert.severity],
                        "title": f"🚨 {alert.severity.upper()}: {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Current Value",
                                "value": f"{alert.current_value:.2f}",
                                "short": True
                            },
                            {
                                "title": "Threshold",
                                "value": f"{alert.threshold:.2f}",
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": alert.status.value,
                                "short": True
                            }
                        ],
                        "footer": "Context Analytics",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            # In production, use aiohttp to send to webhook
            logger.info(f"Would send Slack notification: {json.dumps(payload, indent=2)}")
            return True

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    def __init__(self, smtp_host: str, smtp_port: int, from_addr: str, to_addrs: List[str]):
        """
        Initialize email channel.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    async def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            subject = f"[{alert.severity.upper()}] {alert.rule_name}"
            body = f"""
Alert: {alert.rule_name}
Severity: {alert.severity.value}
Status: {alert.status.value}

Message: {alert.message}

Details:
- Current Value: {alert.current_value:.2f}
- Threshold: {alert.threshold:.2f}
- Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

Alert ID: {alert.alert_id}
            """

            # In production, use aiosmtplib to send email
            logger.info(f"Would send email to {self.to_addrs}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize webhook channel.

        Args:
            webhook_url: Webhook URL
            headers: Optional HTTP headers
        """
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send(self, alert: Alert) -> bool:
        """Send alert to webhook."""
        try:
            payload = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata
            }

            # In production, use aiohttp to POST to webhook
            logger.info(f"Would send webhook to {self.webhook_url}: {json.dumps(payload)}")
            return True

        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False


# ============================================================
# ALERT MANAGER
# ============================================================

class AlertManager:
    """
    Manages alert rules, evaluates conditions, and sends notifications.

    Example:
        manager = AlertManager()

        # Add rules
        manager.add_rule(AlertRule(
            name="high_latency",
            metric="search_latency_p95",
            threshold=0.5,
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.WARNING
        ))

        # Add notification channels
        manager.add_channel(SlackChannel("https://hooks.slack.com/..."))

        # Evaluate metrics
        await manager.evaluate({"search_latency_p95": 0.75})
    """

    def __init__(self):
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.channels: List[NotificationChannel] = []
        self.last_alert_time: Dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule):
        """
        Add an alert rule.

        Args:
            rule: Alert rule to add
        """
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """
        Remove an alert rule.

        Args:
            rule_name: Name of rule to remove
        """
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")

    def add_channel(self, channel: NotificationChannel):
        """
        Add a notification channel.

        Args:
            channel: Notification channel to add
        """
        self.channels.append(channel)
        logger.info(f"Added notification channel: {channel.__class__.__name__}")

    async def evaluate(self, metrics: Dict[str, float]):
        """
        Evaluate all rules against current metrics.

        Args:
            metrics: Dictionary of metric_name -> value
        """
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            # Check if metric exists
            if rule.metric not in metrics:
                continue

            current_value = metrics[rule.metric]

            # Evaluate condition
            triggered = self._evaluate_condition(
                current_value,
                rule.threshold,
                rule.operator
            )

            if triggered:
                await self._handle_triggered_rule(rule, current_value)
            else:
                await self._handle_resolved_rule(rule_name)

    def _evaluate_condition(
        self,
        value: float,
        threshold: float,
        operator: ComparisonOperator
    ) -> bool:
        """Evaluate a single condition."""
        if operator == ComparisonOperator.GREATER_THAN:
            return value > threshold
        elif operator == ComparisonOperator.LESS_THAN:
            return value < threshold
        elif operator == ComparisonOperator.EQUALS:
            return abs(value - threshold) < 0.001
        elif operator == ComparisonOperator.NOT_EQUALS:
            return abs(value - threshold) >= 0.001
        elif operator == ComparisonOperator.GREATER_EQUAL:
            return value >= threshold
        elif operator == ComparisonOperator.LESS_EQUAL:
            return value <= threshold
        return False

    async def _handle_triggered_rule(self, rule: AlertRule, current_value: float):
        """Handle a triggered alert rule."""
        # Check cooldown period
        if rule.name in self.last_alert_time:
            time_since_last = (datetime.now() - self.last_alert_time[rule.name]).total_seconds()
            if time_since_last < rule.cooldown_period:
                return  # Still in cooldown

        # Create alert
        message = (
            rule.description or
            f"{rule.metric} is {rule.operator.value} {rule.threshold} "
            f"(current: {current_value:.2f})"
        )

        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            current_value=current_value,
            threshold=rule.threshold,
            timestamp=datetime.now()
        )

        # Store alert
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        self.last_alert_time[rule.name] = datetime.now()

        # Send notifications
        await self._send_notifications(alert)

        logger.warning(f"Alert triggered: {rule.name} - {message}")

    async def _handle_resolved_rule(self, rule_name: str):
        """Handle a resolved alert."""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()

            # Send resolution notification
            await self._send_notifications(alert)

            # Remove from active alerts
            del self.active_alerts[rule_name]

            logger.info(f"Alert resolved: {rule_name}")

    async def _send_notifications(self, alert: Alert):
        """Send alert to all notification channels."""
        tasks = [channel.send(alert) for channel in self.channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error sending notification via {self.channels[i].__class__.__name__}: {result}"
                )

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """
        Acknowledge an active alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged
        """
        for alert in self.active_alerts.values():
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity

        Returns:
            List of historical alerts
        """
        history = self.alert_history
        if severity:
            history = [a for a in history if a.severity == severity]

        return sorted(history, key=lambda a: a.timestamp, reverse=True)[:limit]


# ============================================================
# ANOMALY DETECTION
# ============================================================

class AnomalyDetector:
    """
    Simple anomaly detection using statistical methods.

    Uses moving average and standard deviation to detect anomalies.
    """

    def __init__(self, window_size: int = 20, std_threshold: float = 3.0):
        """
        Initialize anomaly detector.

        Args:
            window_size: Number of data points for moving window
            std_threshold: Number of standard deviations for anomaly threshold
        """
        self.window_size = window_size
        self.std_threshold = std_threshold
        self.data_windows: Dict[str, List[float]] = {}

    def add_datapoint(self, metric: str, value: float) -> bool:
        """
        Add a datapoint and check for anomaly.

        Args:
            metric: Metric name
            value: Metric value

        Returns:
            True if anomaly detected, False otherwise
        """
        # Initialize window if needed
        if metric not in self.data_windows:
            self.data_windows[metric] = []

        window = self.data_windows[metric]

        # Not enough data yet
        if len(window) < self.window_size:
            window.append(value)
            return False

        # Calculate statistics
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std_dev = variance ** 0.5

        # Check if anomaly
        is_anomaly = abs(value - mean) > (self.std_threshold * std_dev)

        # Update window
        window.append(value)
        if len(window) > self.window_size:
            window.pop(0)

        if is_anomaly:
            logger.warning(
                f"Anomaly detected in {metric}: {value:.2f} "
                f"(mean: {mean:.2f}, std: {std_dev:.2f})"
            )

        return is_anomaly


# ============================================================
# PREDEFINED ALERT RULES
# ============================================================

def get_default_alert_rules() -> List[AlertRule]:
    """Get default alert rules for Context workspace."""
    return [
        # Search Performance
        AlertRule(
            name="high_search_latency",
            metric="search_latency_p95",
            threshold=0.5,  # 500ms
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.WARNING,
            description="Search latency (p95) exceeds 500ms"
        ),
        AlertRule(
            name="critical_search_latency",
            metric="search_latency_p99",
            threshold=2.0,  # 2 seconds
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.CRITICAL,
            description="Search latency (p99) exceeds 2 seconds"
        ),
        AlertRule(
            name="low_cache_hit_rate",
            metric="cache_hit_rate",
            threshold=0.4,  # 40%
            operator=ComparisonOperator.LESS_THAN,
            severity=AlertSeverity.WARNING,
            description="Cache hit rate below 40%"
        ),

        # Index Performance
        AlertRule(
            name="high_index_error_rate",
            metric="index_error_rate",
            threshold=0.05,  # 5%
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.ERROR,
            description="Index error rate exceeds 5%"
        ),
        AlertRule(
            name="large_index_queue",
            metric="index_queue_size",
            threshold=10000,
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.WARNING,
            description="Index queue size exceeds 10,000 files"
        ),

        # System Resources
        AlertRule(
            name="high_memory_usage",
            metric="memory_usage_percentage",
            threshold=0.90,  # 90%
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.CRITICAL,
            description="Memory usage exceeds 90%"
        ),
        AlertRule(
            name="high_cpu_usage",
            metric="cpu_usage_percentage",
            threshold=0.85,  # 85%
            operator=ComparisonOperator.GREATER_THAN,
            severity=AlertSeverity.WARNING,
            description="CPU usage exceeds 85%"
        ),
    ]


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()

        # Add default rules
        for rule in get_default_alert_rules():
            _alert_manager.add_rule(rule)

    return _alert_manager
