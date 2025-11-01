"""
Advanced Monitoring & Alerting (Story 4-3)

Simple in-memory alert registry with thresholds.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Alert:
    key: str
    level: str  # info|warning|critical
    message: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertRegistry:
    def __init__(self):
        self._alerts: List[Alert] = []

    def emit(self, key: str, level: str, message: str):
        self._alerts.append(Alert(key=key, level=level, message=message))

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [a.__dict__ for a in self._alerts][-limit:]

    def clear(self):
        self._alerts.clear()


_registry = AlertRegistry()


def emit_alert(key: str, level: str, message: str):
    _registry.emit(key, level, message)


def list_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    return _registry.list(limit)


def clear_alerts():
    _registry.clear()

