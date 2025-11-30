"""Central logging configuration for the OCR application.

The configuration is expressed as a JSON-friendly dictionary that can be
passed directly to :func:`logging.config.dictConfig`. It wires a rotating file
handler, console logging, and a lightweight JSON formatter so that logs are
structured and easy to ingest by external tools.
"""
from __future__ import annotations

import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Format log records as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def build_logging_config(log_file: Path, level: str = "INFO") -> Dict[str, Any]:
    """Return a dictConfig-ready JSON configuration with rotation enabled."""

    log_file.parent.mkdir(parents=True, exist_ok=True)
    return {
        "version": 1,
        "formatters": {
            "json": {
                "()": JsonFormatter,
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
            "console": {
                "format": "%(levelname)s: %(message)s",
            },
        },
        "handlers": {
            "file": {
                "class": RotatingFileHandler.__module__ + ".RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_file),
                "maxBytes": 5_000_000,
                "backupCount": 3,
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": level,
            },
        },
        "root": {
            "handlers": ["file", "console"],
            "level": level,
        },
        "disable_existing_loggers": False,
    }


def configure_logging(log_file: Path, level: str = "INFO") -> None:
    """Apply the JSON logging configuration globally."""

    logging.config.dictConfig(build_logging_config(log_file, level))

