"""
Unit tests for Usage Analytics (Story 5-3)
"""

from src.analytics.usage import usage


def test_usage_counters():
    u = usage()
    u.reset()
    u.incr("tools_called")
    u.incr("tools_called", 2)
    assert u.get("tools_called") == 3
    assert "tools_called" in u.all()
