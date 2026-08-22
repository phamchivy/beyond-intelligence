"""Structured JSON logging to stdout. No ``print()`` outside tests and scripts.

Mirrors ``agent/observability/logging.py`` field-for-field so both Python
pods emit the same shape and can be collected/routed the same way.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Renders each log record as one JSON object: timestamp, level, event, fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Build the JSON payload for one log record."""
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload.update(extra_fields)
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a JSON-to-stdout logger for ``name``, configured once.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` with one stdout handler, safe to call
        repeatedly with the same name without duplicating handlers.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    """Log one structured event, never a free-text string.

    Args:
        logger: A logger obtained from :func:`get_logger`.
        level: One of ``"debug"``, ``"info"``, ``"warning"``, ``"error"``.
        event: A short snake_case event name, e.g. ``"asset_extracted"``.
        **fields: Structured fields attached to the event -- never a
            transcript, a full record payload, or anything classified
            ``pii``.
    """
    getattr(logger, level.lower())(event, extra={"extra_fields": fields})


@contextmanager
def log_duration(logger: logging.Logger, event: str, **fields: Any) -> Iterator[None]:
    """Time a block of code and log ``duration_ms`` on exit, including on error.

    Args:
        logger: A logger obtained from :func:`get_logger`.
        event: The event name to log when the block finishes.
        **fields: Extra structured fields to attach.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log_event(logger, "info", event, duration_ms=duration_ms, **fields)
