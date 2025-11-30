"""Application bootstrap."""
from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import TYPE_CHECKING, NoReturn, TypeAlias

if TYPE_CHECKING:
    import PyQt6.QtWidgets as QtWidgets

    QtWidgetsModule: TypeAlias = QtWidgets
else:
    QtWidgetsModule: TypeAlias = ModuleType


def _is_headless_environment() -> bool:
    """Return True when no display server is available."""

    has_display = any(os.environ.get(var) for var in ("DISPLAY", "WAYLAND_DISPLAY"))
    return not sys.platform.startswith("win") and not has_display and "QT_QPA_PLATFORM" not in os.environ


def _set_default_font_dir() -> None:
    """Point Qt to a known font directory when running headless."""

    if "QT_QPA_FONTDIR" in os.environ:
        return

    candidate_paths = (
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
    )
    for path in candidate_paths:
        if os.path.isdir(path):
            os.environ["QT_QPA_FONTDIR"] = path
            break


def _prepare_qt_environment() -> None:
    """Configure Qt to work in headless containers and avoid sandbox issues."""

    headless = _is_headless_environment()

    if headless:
        # Force software rendering to sidestep missing GPU/GL drivers in CI or containers.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # Chromium-based components (e.g., QtWebEngine) require the flag below in containers.
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")
        _set_default_font_dir()


def _import_qt() -> QtWidgetsModule:
    """Import PyQt6 with a clear error message for missing system libraries."""

    try:
        import PyQt6.QtWidgets as QtWidgets
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific
        # PyQt6 or its Qt runtime is not installed at all.
        message = (
            "Nie można załadować PyQt6 (brak modułu QtWidgets). "
            "Upewnij się, że zainstalowano `PyQt6` zgodnie z `requirements.txt` "
            "(`pip install -r requirements.txt`)."
        )
        raise SystemExit(message) from exc
    except ImportError as exc:  # pragma: no cover - environment-specific
        error_text = str(exc)
        missing_gl = "libGL.so.1" in error_text
        missing_qtwidgets = "QtWidgets" in error_text

        if missing_gl:
            message = (
                "Nie można załadować PyQt6 (brak libGL.so.1). "
                "Zainstaluj systemową bibliotekę OpenGL (np. `sudo apt-get install libgl1` "
                "lub `sudo dnf install mesa-libGL`) i ponów próbę."
            )
        elif missing_qtwidgets:
            message = (
                "Nie można załadować modułu QtWidgets w PyQt6. "
                "Upewnij się, że zainstalowano pełny pakiet PyQt6 zgodnie z `requirements.txt` "
                "(`pip install --no-cache-dir -r requirements.txt`) oraz że używasz 64-bitowego Pythona. "
                "Na Windowsie doinstaluj najnowszy Visual C++ Redistributable x64."
            )
        else:
            message = (
                "Nie można załadować PyQt6. "
                "Sprawdź instalację (`pip install --no-cache-dir -r requirements.txt`)."
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
