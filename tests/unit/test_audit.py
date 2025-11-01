"""
Unit tests for Audit Logging (Story 4-2)
"""
import os
from src.security.audit import record_event, read_events, LOG_FILE


def test_audit_record_and_read(tmp_path, monkeypatch):
    # Redirect audit log to temp dir
    log_file = tmp_path / "audit.log"
    monkeypatch.setattr("src.security.audit.LOG_FILE", str(log_file), raising=False)

    record_event("test", "tester", {"x": 1})
    record_event("test", "tester", {"x": 2})

    events = read_events()
    assert len(events) == 2
    assert events[0]["type"] == "test"

