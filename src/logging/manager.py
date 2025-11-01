"""
Logging Manager (Enterprise-ready)

Centralized logging configuration with optional JSON formatting.
"""

import logging
import json
import sys
import contextvars
from datetime import datetime, timezone
from typing import Optional

# Correlation ID context var
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        cid = _correlation_id.get()
        if cid:
            payload["correlation_id"] = cid
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
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
    logging.root.addHandler(handler)


# Correlation ID helpers


def set_correlation_id(correlation_id: Optional[str]) -> None:
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
