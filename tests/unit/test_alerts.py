"""
Unit tests for Alerts (Story 4-3)
"""
from src.monitoring.alerts import emit_alert, list_alerts, clear_alerts


def test_alerts_flow():
    clear_alerts()
    emit_alert("cpu", "warning", "High CPU")
    emit_alert("db", "critical", "DB down")

    alerts = list_alerts()
    assert len(alerts) == 2
    assert any(a["level"] == "critical" for a in alerts)

