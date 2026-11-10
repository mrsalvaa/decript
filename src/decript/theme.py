# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema claro/oscuro e íconos vectoriales propios (sin archivos externos)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

LIGHT = {
    "bg": "#f4f6fa",
    "surface": "#ffffff",
    "surface2": "#eef1f6",
    "border": "#dde2ea",
    "text": "#141a24",
    "muted": "#5b6577",
    "accent": "#0f7fb8",
    "accent_hover": "#0c6c9d",
    "accent_text": "#ffffff",
    "accent_soft": "#e1f1f9",
    "ok": "#17794a",
    "ok_soft": "#e0f4ea",
    "err": "#b3261e",
    "err_soft": "#fbe6e4",
    "sel": "#dcedf7",
}

DARK = {
    "bg": "#10141b",
    "surface": "#181d27",
    "surface2": "#212836",
    "border": "#2b3445",
    "text": "#e8ecf3",
    "muted": "#98a3b6",
    "accent": "#3fb6ec",
    "accent_hover": "#63c5f1",
    "accent_text": "#06202c",
    "accent_soft": "#143447",
    "ok": "#58d39a",
    "ok_soft": "#143326",
    "err": "#ff8a80",
    "err_soft": "#3d1a18",
    "sel": "#1c3a4d",
}


def palette(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def stylesheet(c: dict[str, str]) -> str:
    return f"""
* {{ font-size: 10.5pt; }}
QWidget#root, QDialog {{ background: {c['bg']}; color: {c['text']}; }}
QLabel {{ color: {c['text']}; background: transparent; }}
QLabel#title {{ font-size: 15pt; font-weight: 700; letter-spacing: -0.3px; }}
QLabel#muted, QLabel#status {{ color: {c['muted']}; }}
QLabel#emptyTitle {{ font-size: 14pt; font-weight: 600; color: {c['text']}; }}
QLabel#emptySub {{ color: {c['muted']}; }}
QLabel#chip {{ border-radius: 12px; padding: 4px 12px; background: {c['surface2']}; color: {c['muted']}; font-weight: 600; }}
QLabel#chip[state="ok"] {{ background: {c['ok_soft']}; color: {c['ok']}; }}
QLabel#msgOk {{ color: {c['ok']}; }}
QLabel#msgErr {{ color: {c['err']}; }}
QLabel#mono {{ font-family: monospace; font-size: 9pt; color: {c['text']}; background: {c['surface2']}; border-radius: 8px; padding: 8px 10px; }}

QFrame#card {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 14px; }}
QFrame#drop {{ background: transparent; border: 2px dashed {c['border']}; border-radius: 14px; }}
QFrame#drop[active="true"] {{ border-color: {c['accent']}; background: {c['accent_soft']}; }}

QPushButton {{
    background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 10px; padding: 8px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {c['surface2']}; }}
QPushButton:pressed {{ background: {c['sel']}; }}
QPushButton:disabled {{ color: {c['muted']}; background: {c['surface2']}; border-color: {c['surface2']}; }}
QPushButton:focus {{ border: 2px solid {c['accent']}; padding: 7px 13px; }}
QPushButton#primary {{ background: {c['accent']}; color: {c['accent_text']}; border: 1px solid {c['accent']}; }}
QPushButton#primary:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton#primary:disabled {{ background: {c['surface2']}; color: {c['muted']}; border-color: {c['surface2']}; }}
QPushButton#primary:focus {{ border: 2px solid {c['text']}; }}
QPushButton#flat {{ border: none; background: transparent; padding: 8px 10px; color: {c['muted']}; }}
QPushButton#flat:hover {{ background: {c['surface2']}; color: {c['text']}; }}
QPushButton#flat:focus {{ border: 2px solid {c['accent']}; padding: 6px 8px; }}

QLineEdit {{
    background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 10px; padding: 8px 10px; selection-background-color: {c['accent']}; selection-color: {c['accent_text']};
}}
QLineEdit:focus {{ border: 2px solid {c['accent']}; padding: 7px 9px; }}

QTreeWidget {{
    background: {c['surface']}; color: {c['text']}; border: none; outline: 0;
    alternate-background-color: {c['surface']};
}}
QTreeWidget::item {{ padding: 9px 6px; border-bottom: 1px solid {c['surface2']}; }}
QTreeWidget::item:hover {{ background: {c['surface2']}; }}
QTreeWidget::item:selected {{ background: {c['sel']}; color: {c['text']}; }}
QHeaderView::section {{
    background: {c['surface']}; color: {c['muted']}; border: none; border-bottom: 1px solid {c['border']};
    padding: 9px 8px; font-weight: 600; font-size: 9.5pt;
}}
QProgressBar {{ background: {c['surface2']}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QToolTip {{ background: {c['text']}; color: {c['bg']}; border: none; padding: 5px 8px; border-radius: 6px; }}
"""


# Íconos propios, trazo de 2 px en una grilla de 24
_ICONS = {
    "add": '<path d="M12 5v14M5 12h14"/>',
    "remove": '<path d="M5 12h14"/>',
    "clear": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l3 3M14 9l2 2"/>',
    "export": '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "alert": '<path d="M12 4l9 16H3zM12 10v4M12 17.5v.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "file": '<path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM14 3v5h5"/>',
}


def _render(name: str, color: str, px: int) -> QPixmap:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_ICONS[name]}</svg>'
    )
    pix = QPixmap(QSize(px, px))
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return pix


def icon(name: str, color: str, size: int = 20, disabled: str | None = None) -> QIcon:
    """Ícono de un color; `disabled` es el color cuando el botón está deshabilitado."""
    result = QIcon()
    for scale in (1, 2):
        pix = _render(name, color, size * scale)
        pix.setDevicePixelRatio(scale)
        result.addPixmap(pix, QIcon.Mode.Normal)
        off = _render(name, disabled or color, size * scale)
        off.setDevicePixelRatio(scale)
        result.addPixmap(off, QIcon.Mode.Disabled)
    return result


def app_icon() -> QIcon:
    """Ícono de la app: candado abierto sobre fondo cian."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#35b8ee"/><stop offset="1" stop-color="#0b6a9c"/></linearGradient></defs>'
        '<rect x="16" y="16" width="224" height="224" rx="56" fill="url(#g)"/>'
        '<path d="M92 118V86a36 36 0 0 1 70-12" fill="none" stroke="#fff" stroke-width="16" stroke-linecap="round"/>'
        '<rect x="68" y="118" width="120" height="86" rx="20" fill="#fff"/>'
        '<path d="M128 148v26" stroke="#0b6a9c" stroke-width="16" stroke-linecap="round"/>'
        "</svg>"
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    result = QIcon()
    for size in (32, 64, 128, 256):
        pix = QPixmap(QSize(size, size))
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        result.addPixmap(pix)
    return result

