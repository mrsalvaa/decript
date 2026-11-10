# SPDX-License-Identifier: GPL-3.0-or-later
"""Exporta el ícono de la app a PNG. Uso: QT_QPA_PLATFORM=offscreen python make_icon.py salida.png [tamaño]"""
import sys

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from decript import theme

app = QApplication(sys.argv)
size = int(sys.argv[2]) if len(sys.argv) > 2 else 256
theme.app_icon().pixmap(QSize(size, size)).save(sys.argv[1])
