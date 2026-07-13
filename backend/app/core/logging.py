"""Structured JSON logging + a request-id context (N6: observability)."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Merge any structured extras passed via logger.info(..., extra={"extra": {...}})
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Quiet noisy libraries a touch.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
