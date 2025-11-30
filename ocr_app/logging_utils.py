"""Logging helpers for the OCR application."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import config


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
    """Configure root logger with file and optional GUI handlers."""
    cfg_file = log_file or config.log_file
    logger = logging.getLogger("ocr_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(cfg_file, maxBytes=5_000_000, backupCount=3)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(console_handler)

        if gui_signal is not None:
            gui_handler = QtLogHandler(gui_signal)
            gui_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(gui_handler)

    return logger
