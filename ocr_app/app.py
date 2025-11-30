"""Application bootstrap."""
from __future__ import annotations

import sys

from PyQt5 import QtWidgets

from .gui.main_window import MainWindow


def main() -> None:
    """Start the OCR GUI application."""
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
