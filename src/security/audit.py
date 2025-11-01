"""
Auditing & Compliance Logging (Story 4-2)

Writes audit events as JSON lines to logs/audit.log
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "audit.log")

os.makedirs(LOG_DIR, exist_ok=True)


def record_event(event_type: str, actor: str, details: Dict[str, Any]):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "actor": actor,
        "details": details,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_events(limit: int = 100):
    if not os.path.exists(LOG_FILE):
        return []
    lines = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            lines.append(json.loads(line))
    return lines[-limit:]
