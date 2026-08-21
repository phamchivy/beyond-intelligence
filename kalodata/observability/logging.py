"""
Vi tri file nay: data/observability/logging.py

Logging co cau truc, cung pattern da dung cho agent/observability/logging.py
-- day la ban Python doc lap (khong import chung giua 2 container).
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

from config.settings import settings


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
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
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(settings.observability.log_level.value)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    getattr(logger, level.lower())(event, extra={"extra_fields": fields})


@contextmanager
def log_duration(logger: logging.Logger, event: str, **fields: Any) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(logger, "info", event, duration_ms=duration_ms, **fields)