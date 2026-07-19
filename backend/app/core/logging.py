"""Structured JSON logging configuration using structlog.

This module provides structured logging with JSON output in production
and human-readable output in development, using structlog as the
backbone while integrating with Python's standard logging.

Requirements: 41.1, 41.5
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any


def configure_logging() -> None:
    """Configure structlog for structured JSON or console logging.

    Reads ``LOG_FORMAT`` from the environment:
    - ``json``    → machine-parseable JSON (default, for production)
    - ``console`` → human-readable coloured output (for development)

    The ``LOG_LEVEL`` env variable controls verbosity (default ``INFO``).
    """
    try:
        import structlog  # optional dependency — graceful degradation
    except ImportError:
        # structlog not installed; fall back to stdlib JSON logging already
        # configured by backend.app.infrastructure.logging.logger
        logging.getLogger(__name__).warning(
            "structlog not installed — structured logging is unavailable. "
            "Install it with: pip install structlog==24.4.0"
        )
        return

    log_format = os.getenv("LOG_FORMAT", "json").lower()
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    if log_format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )

    # Ensure stdlib root logger is also configured at the same level so
    # libraries that use standard ``logging`` still emit output.
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        root.addHandler(handler)
    root.setLevel(log_level)


def get_structlog_logger(name: str):  # type: ignore[return]
    """Return a structlog bound logger for the given module name."""
    try:
        import structlog
        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)
