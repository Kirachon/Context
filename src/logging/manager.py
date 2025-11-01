"""
Logging Manager (Enterprise-ready)

Centralized logging configuration with optional JSON formatting.
"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", fmt: str = "json"):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.root.handlers.clear()
    logging.root.setLevel(lvl)
    handler = logging.StreamHandler(sys.stdout)
    if fmt.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logging.root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
