"""Application bootstrap."""
from __future__ import annotations

import os
import sys
from typing import NoReturn


def _prepare_qt_environment() -> None:
    """Configure Qt to work in headless containers and avoid sandbox issues."""

    # Force software rendering to sidestep missing GPU/GL drivers in CI or containers.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Chromium-based components (e.g., QtWebEngine) require the flag below in containers.
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")


def _import_qt() -> "QtWidgets":
    """Import PyQt5 with a clear error message for missing system libraries."""

    try:
        from PyQt5 import QtWidgets
    except ImportError as exc:  # pragma: no cover - environment-specific
        missing_gl = "libGL.so.1" in str(exc)
        help_hint = (
            "Zainstaluj systemową bibliotekę OpenGL (np. `sudo apt-get install libgl1` "
            "lub `sudo dnf install mesa-libGL`) i ponów próbę."
        )
        message = (
            "Nie można załadować PyQt5. "
            + ("Brakuje libGL.so.1. " if missing_gl else "")
            + help_hint
        )
        raise SystemExit(message) from exc
    return QtWidgets


def main() -> NoReturn:
    """Start the OCR GUI application."""

    _prepare_qt_environment()
    QtWidgets = _import_qt()
    from .gui.main_window import MainWindow
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
