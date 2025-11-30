"""Logging helpers and lightweight metrics for the OCR application."""
from __future__ import annotations

import csv
import logging
import logging.config
from pathlib import Path
from typing import Dict, List, Optional

from .config import config
from .logging_config import configure_logging


class QtLogHandler(logging.Handler):
    """Custom handler to forward log messages to a Qt signal."""

    def __init__(self, signal=None) -> None:
        super().__init__()
        self.signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        if self.signal:
            try:
                self.signal.emit(msg)
            except Exception:
                # Fall back to stdout if signal fails
                print(msg)


def setup_logging(log_file: Optional[Path] = None, gui_signal=None) -> logging.Logger:
    """Configure root logger with file, console, and optional GUI handlers."""

    cfg_file = log_file or config.log_file
    configure_logging(cfg_file)
    logger = logging.getLogger("ocr_app")
    logger.propagate = True

    if gui_signal is not None:
        gui_handler = QtLogHandler(gui_signal)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(gui_handler)

    return logger


def record_metrics(rows: List[Dict[str, object]], metrics_file: Optional[Path] = None) -> None:
    """Append pipeline metrics to a CSV file."""

    path = metrics_file or config.metrics_file
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    if not rows:
        return

    with path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=sorted(rows[0].keys()))
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
