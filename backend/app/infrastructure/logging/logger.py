from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, Optional

from backend.app.infrastructure.context.request_context import (
    get_correlation_id,
    get_tenant_id,
    get_user_id,
)


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            # Request context — read from ContextVars automatically
            "correlation_id": get_correlation_id(),
            "tenant_id": get_tenant_id(),
            "user_id": get_user_id(),
        }
        # Merge extra fields passed by the caller
        for key, value in record.__dict__.items():
            if key not in (
                "msg", "args", "levelname", "name", "pathname",
                "filename", "module", "exc_info", "exc_text",
                "stack_info", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "taskName",
            ) and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _setup_root_logger(level: str) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # Already configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Return a logger pre-configured with JSON formatting and auto-populated
    correlation_id / tenant_id / user_id from ContextVars.

    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": str(user.id)})
    """
    from backend.app.config import get_settings
    settings = get_settings()
    _setup_root_logger(level or settings.log_level)
    return logging.getLogger(name)
