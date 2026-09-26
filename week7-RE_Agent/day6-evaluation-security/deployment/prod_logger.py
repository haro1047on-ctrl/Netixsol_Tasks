"""Task 5: Production JSON-Structured Logging Subsystem."""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with ISO 8601 timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include custom extra fields if provided
        if hasattr(record, "request_id"):
            log_payload["request_id"] = getattr(record, "request_id")
        if hasattr(record, "session_id"):
            log_payload["session_id"] = getattr(record, "session_id")
        if hasattr(record, "latency_ms"):
            log_payload["latency_ms"] = getattr(record, "latency_ms")
        if hasattr(record, "intent"):
            log_payload["intent"] = getattr(record, "intent")

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_production_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with structured JSON streaming."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(stream_handler)

    return root_logger


# Global logger instance
prod_logger = logging.getLogger("RealEstateHubProd")
