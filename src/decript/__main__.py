# SPDX-License-Identifier: GPL-3.0-or-later
"""Punto de entrada: `python -m decript [archivos .age…]`."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import __version__, i18n, theme
from .ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("decript")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("decript")
    app.setStyle("Fusion")
    app.setWindowIcon(theme.app_icon())
    i18n.set_language(i18n.system_language())
    window = MainWindow()
    window.show()
    paths = [a for a in app.arguments()[1:] if not a.startswith("-")]
    if paths:
        window.add_paths(paths)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
