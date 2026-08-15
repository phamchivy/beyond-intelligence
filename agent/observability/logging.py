"""
observability/logging.py -- logging co cau truc (structured), dung
CHUNG cho application/ va infrastructure/. KHONG duoc dung trong
domain/ -- domain phai giu "pure", khong biet logging ton tai.

Nguyen tac (theo tai lieu kien truc da thong nhat):
  - Tuyet doi khong dung print().
  - Log co cau truc (JSON: event + field ro rang), khong noi thong tin
    vao 1 chuoi text tu do -- de sau nay gan OpenTelemetry/Langfuse ma
    khong phai sua lai cach log.
  - KHONG log toan bo prompt/du lieu nguoi dung mac dinh (settings.
    observability.log_prompts phai bat tuong minh moi log prompt that).
  - Log level doc tu settings.observability.log_level, khong hardcode.
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
    """
    Lay logger co cau hinh san (JSON, ghi ra stdout, level theo settings).
    Goi nhieu lan voi cung `name` se tra ve cung 1 logger, khong tao
    handler trung lap.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(settings.observability.log_level.value)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    """
    Ghi mot dong log co cau truc.

    Dung thay cho `logger.info("mot chuoi tu do")` -- moi thong tin lien
    quan (task_id, model, tokens, duration_ms...) di kem duoi dang field
    rieng, khong noi vao chuoi text, de log co the query/filter duoc.
    """
    getattr(logger, level.lower())(event, extra={"extra_fields": fields})


@contextmanager
def log_duration(logger: logging.Logger, event: str, **fields: Any) -> Iterator[None]:
    """
    Context manager do thoi gian thuc thi mot khoi code, tu dong ghi
    `duration_ms` vao log khi ket thuc (ke ca khi co exception).

    Vi du:
        with log_duration(logger, "llm_call_completed", model=model_name):
            response = await llm.generate(request)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(logger, "info", event, duration_ms=duration_ms, **fields)