# SPDX-License-Identifier: GPL-3.0-or-later
"""Ventana principal de decript."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import core, i18n, theme
from .i18n import tr

COL_FILE, COL_TYPE, COL_SIZE, COL_DATE, COL_STATUS = range(5)


def destination() -> Path:
    """Carpeta de exportación: ~/decript (DECRIPT_DEST la cambia, para pruebas)."""
    return Path(os.environ.get("DECRIPT_DEST") or Path.home() / "decript")


def pretty(path: Path) -> str:
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def short_pub(pub: str) -> str:
    return pub if len(pub) <= 20 else f"{pub[:10]}…{pub[-6:]}"


@dataclass
class Entry:
    path: Path
    size: int
    mtime: float
    status: str = "pending"  # pending | decrypting | extracting | done | error
    detail: str = ""  # texto del error ya traducible: clave de i18n
    detail_args: dict = field(default_factory=dict)
    folder: Path | None = None
    files: int = 0
    kind: str = ""


def error_key(exc: Exception) -> tuple[str, dict]:
    if isinstance(exc, core.DecriptError):
        return f"err_{exc.code}", {}
    if isinstance(exc, FileNotFoundError):
        return "err_missing", {}
    if isinstance(exc, OSError):
        return "err_io", {"detail": exc.strerror or str(exc)}
    return "err_error", {"detail": str(exc)}


# ── Trabajo en segundo plano ───────────────────────────────────────────────────

class ExportWorker(QObject):
    stage = Signal(int, str)
    done = Signal(int, object)
    failed = Signal(int, str, dict)
    finished = Signal()

    def __init__(self, jobs: list[tuple[int, Path]], identities: list, dest: Path):
        super().__init__()
        self._jobs = jobs
        self._identities = identities
        self._dest = dest

    @Slot()
    def run(self) -> None:
        for index, path in self._jobs:
            try:
                result = core.export_file(path, self._identities, self._dest, lambda s, i=index: self.stage.emit(i, s))
                self.done.emit(index, result)
            except Exception as exc:  # cada archivo falla por separado
                key, args = error_key(exc)
                self.failed.emit(index, key, args)
        self.finished.emit()


# ── Diálogo de clave ───────────────────────────────────────────────────────────

class KeyDialog(QDialog):
    def __init__(self, parent: QWidget, colors: dict, has_key: bool):
        super().__init__(parent)
        self.identities: list | None = None
        self.forget = False
        self._colors = colors
        self.setWindowTitle(tr("key_title"))
        self.setModal(True)
        self.setMinimumWidth(640)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)

        title = QLabel(tr("key_title"))
        title.setObjectName("title")
        lay.addWidget(title)

        intro = QLabel(tr("key_intro"))
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        lay.addWidget(intro)

        self.choose = QPushButton(theme.icon("file", colors["text"]), " " + tr("key_choose"))
        self.choose.clicked.connect(self._choose_file)
        row = QHBoxLayout()
        row.addWidget(self.choose)
        self.file_label = QLabel("")
        self.file_label.setObjectName("muted")
        row.addWidget(self.file_label, 1)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("key_paste_ph"))
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setAccessibleName(tr("key_title"))
        self.edit.textChanged.connect(self._text_changed)
        row2.addWidget(self.edit, 1)
        self.toggle = QPushButton(tr("key_show"))
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self._toggle_echo)
        row2.addWidget(self.toggle)
        lay.addLayout(row2)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        self.pub = QLabel("")
        self.pub.setObjectName("mono")
        self.pub.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.pub.setWordWrap(True)
        self.pub.hide()
        lay.addWidget(self.pub)

        buttons = QHBoxLayout()
        if has_key:
            forget = QPushButton(tr("key_forget"))
            forget.clicked.connect(self._forget)
            buttons.addWidget(forget)
        buttons.addStretch(1)
        cancel = QPushButton(tr("cancel"))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self.use = QPushButton(tr("key_use"))
        self.use.setObjectName("primary")
        self.use.setDefault(True)
        self.use.setEnabled(False)
        self.use.clicked.connect(self.accept)
        buttons.addWidget(self.use)
        lay.addSpacing(4)
        lay.addLayout(buttons)

    def _toggle_echo(self, shown: bool) -> None:
        self.edit.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)
        self.toggle.setText(tr("key_hide") if shown else tr("key_show"))

    def _set_result(self, identities: list | None, error: str = "") -> None:
        self.identities = identities
        self.use.setEnabled(bool(identities))
        if identities:
            pubs = core.public_keys(identities)
            self.msg.setObjectName("msgOk")
            self.msg.setText(tr("key_ok") if len(pubs) == 1 else tr("key_ok_many", n=len(pubs)))
            self.pub.setText("\n".join(pubs))
            self.pub.show()
        else:
            self.msg.setObjectName("msgErr")
            self.msg.setText(error)
            self.pub.hide()
        self.msg.style().unpolish(self.msg)
        self.msg.style().polish(self.msg)

    def _text_changed(self, text: str) -> None:
        self.file_label.setText("")
        if not text.strip():
            self._set_result(None)
            return
        try:
            self._set_result(core.parse_identities(text))
        except core.DecriptError as exc:
            self._set_result(None, tr(f"err_{exc.code}"))

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("key_title"), str(Path.home()), tr("key_file_filter"))
        if not path:
            return
        self.edit.blockSignals(True)
        self.edit.clear()
        self.edit.blockSignals(False)
        self.file_label.setText(Path(path).name)
        try:
            self._set_result(core.load_identities_file(path))
        except core.DecriptError as exc:
            self._set_result(None, tr(f"err_{exc.code}"))
        except OSError as exc:
            self._set_result(None, tr("err_read_key", detail=exc.strerror or str(exc)))

    def _forget(self) -> None:
        self.forget = True
        self.reject()


# ── Ventana principal ──────────────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle("decript")
        self.setWindowIcon(theme.app_icon())
        self.resize(980, 620)
        self.setMinimumSize(720, 440)
        self.setAcceptDrops(True)

        self.entries: list[Entry] = []
        self.identities: list | None = None
        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None
        self._total = 0
        self._finished = 0
        self._last_status: tuple[str, dict] = ("status_ready", {})
        self.colors = theme.palette(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 12)
        root.setSpacing(12)

        # Cabecera
        head = QHBoxLayout()
        head.setSpacing(8)
        self.logo = QLabel()
        self.logo.setPixmap(theme.app_icon().pixmap(QSize(30, 30)))
        head.addWidget(self.logo)
        self.title = QLabel("decript")
        self.title.setObjectName("title")
        head.addWidget(self.title)
        head.addSpacing(10)
        self.chip = QLabel()
        self.chip.setObjectName("chip")
        head.addWidget(self.chip)
        head.addStretch(1)
        self.btn_lang = QPushButton()
        self.btn_lang.setObjectName("flat")
        self.btn_lang.clicked.connect(self.toggle_language)
        head.addWidget(self.btn_lang)
        root.addLayout(head)

        # Barra de acciones
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_add = QPushButton()
        self.btn_remove = QPushButton()
        self.btn_clear = QPushButton()
        self.btn_key = QPushButton()
        self.btn_open = QPushButton()
        self.btn_export = QPushButton()
        self.btn_export.setObjectName("primary")
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_list)
        self.btn_key.clicked.connect(self.ask_key)
        self.btn_open.clicked.connect(self.open_destination)
        self.btn_export.clicked.connect(self.export)
        for b in (self.btn_add, self.btn_remove, self.btn_clear):
            bar.addWidget(b)
        bar.addStretch(1)
        for b in (self.btn_key, self.btn_open, self.btn_export):
            bar.addWidget(b)
        root.addLayout(bar)

        # Lista / estado vacío
        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(1, 1, 1, 1)
        self.stack = QStackedWidget()
        card_lay.addWidget(self.stack)

        empty = QWidget()
        empty_lay = QVBoxLayout(empty)
        empty_lay.setContentsMargins(22, 22, 22, 22)
        self.drop = QFrame()
        self.drop.setObjectName("drop")
        drop_lay = QVBoxLayout(self.drop)
        drop_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_lay.setSpacing(8)
        self.empty_icon = QLabel()
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_sub = QLabel()
        self.empty_sub.setObjectName("emptySub")
        self.empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_sub.setWordWrap(True)
        for w in (self.empty_icon, self.empty_title, self.empty_sub):
            drop_lay.addWidget(w)
        empty_lay.addWidget(self.drop)
        self.stack.addWidget(empty)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_FILE, QHeaderView.ResizeMode.Stretch)
        for col in (COL_TYPE, COL_SIZE, COL_DATE):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(COL_STATUS, 300)
        header.setSectionsMovable(False)
        self.tree.itemSelectionChanged.connect(self.update_buttons)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.stack.addWidget(self.tree)
        root.addWidget(card, 1)

        # Pie
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        root.addWidget(self.progress)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.status)

        # Atajos
        QShortcut(QKeySequence.StandardKey.Open, self, self.pick_files)
        QShortcut(QKeySequence("Ctrl+K"), self, self.ask_key)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export)
        QShortcut(QKeySequence.StandardKey.Delete, self.tree, self.remove_selected)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        hints = QGuiApplication.styleHints()
        hints.colorSchemeChanged.connect(lambda _s: self.apply_theme())
        self.apply_theme()

    # ── Tema e idioma ──

    def apply_theme(self) -> None:
        forced = os.environ.get("DECRIPT_THEME", "")
        if forced in ("dark", "light"):
            dark = forced == "dark"
        else:
            dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self.colors = theme.palette(dark)
        self.setStyleSheet(theme.stylesheet(self.colors))
        c = self.colors
        self.btn_add.setIcon(theme.icon("add", c["text"], disabled=c["muted"]))
        self.btn_remove.setIcon(theme.icon("remove", c["text"], disabled=c["muted"]))
        self.btn_clear.setIcon(theme.icon("clear", c["text"], disabled=c["muted"]))
        self.btn_key.setIcon(theme.icon("key", c["text"], disabled=c["muted"]))
        self.btn_open.setIcon(theme.icon("folder", c["text"], disabled=c["muted"]))
        self.btn_export.setIcon(theme.icon("export", c["accent_text"], disabled=c["muted"]))
        self.empty_icon.setPixmap(theme.icon("lock", c["muted"], 44).pixmap(QSize(44, 44)))
        self.retranslate()

    def toggle_language(self) -> None:
        i18n.set_language("en" if i18n.language() == "es" else "es")
        self.retranslate()

    def retranslate(self) -> None:
        dest = pretty(destination())
        self.btn_add.setText(" " + tr("add"))
        self.btn_add.setToolTip(tr("add_tip"))
        self.btn_remove.setText(" " + tr("remove"))
        self.btn_remove.setToolTip(tr("remove_tip"))
        self.btn_clear.setText(" " + tr("clear"))
        self.btn_clear.setToolTip(tr("clear_tip"))
        self.btn_key.setText(" " + tr("key"))
        self.btn_key.setToolTip(tr("key_tip"))
        self.btn_export.setText(" " + tr("export"))
        self.btn_export.setToolTip(tr("export_tip", dest=dest))
        self.btn_open.setText(" " + tr("open_folder"))
        self.btn_open.setToolTip(tr("open_folder_tip", dest=dest))
        self.btn_lang.setText("")
        self.btn_lang.setIcon(theme.flag(i18n.language()))
        self.btn_lang.setIconSize(QSize(27, 18))
        self.btn_lang.setToolTip(tr("lang_tip"))
        self.btn_lang.setAccessibleName(tr("lang_tip"))
        self.empty_title.setText(tr("empty_title"))
        self.empty_sub.setText(tr("empty_sub"))
        self.tree.setHeaderLabels([tr("col_file"), tr("col_type"), tr("col_size"), tr("col_date"), tr("col_status")])
        self.tree.headerItem().setTextAlignment(COL_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.update_chip()
        for i in range(len(self.entries)):
            self.refresh_row(i)
        self.set_status(*self._last_status)
        self.update_buttons()

    def set_status(self, key: str, args: dict | None = None) -> None:
        self._last_status = (key, args or {})
        merged = {"dest": pretty(destination()), **(args or {})}
        self.status.setText(tr(key, **merged))

    def update_chip(self) -> None:
        if self.identities:
            pub = short_pub(core.public_keys(self.identities)[0])
            self.chip.setText(tr("key_loaded", pub=pub))
            self.chip.setProperty("state", "ok")
        else:
            self.chip.setText(tr("key_none"))
            self.chip.setProperty("state", "")
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)

    # ── Lista ──

    def busy(self) -> bool:
        return self._thread is not None

    def update_buttons(self) -> None:
        busy = self.busy()
        has = bool(self.entries)
        self.stack.setCurrentIndex(1 if has else 0)
        self.btn_add.setEnabled(not busy)
        self.btn_key.setEnabled(not busy)
        self.btn_remove.setEnabled(not busy and bool(self.tree.selectedItems()))
        self.btn_clear.setEnabled(not busy and has)
        self.btn_export.setEnabled(not busy and any(e.status in ("pending", "error") for e in self.entries))

    def format_date(self, ts: float) -> str:
        fmt = "%d-%m-%Y %H:%M" if i18n.language() == "es" else "%Y-%m-%d %H:%M"
        return time.strftime(fmt, time.localtime(ts))

    def refresh_row(self, index: int) -> None:
        e = self.entries[index]
        item = self.tree.topLevelItem(index)
        c = self.colors
        item.setText(COL_FILE, e.path.name)
        item.setIcon(COL_FILE, theme.icon("lock" if e.status != "done" else "folder", c["muted"], 18))
        item.setToolTip(COL_FILE, str(e.path))
        item.setText(COL_TYPE, tr(f"kind_{e.kind or core.guess_kind(e.path)}"))
        item.setText(COL_SIZE, i18n.human_size(e.size))
        item.setTextAlignment(COL_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setText(COL_DATE, self.format_date(e.mtime))
        for col in (COL_TYPE, COL_SIZE, COL_DATE):
            item.setForeground(col, _brush(c["muted"]))

        tip = ""
        if e.status == "done":
            text = tr("st_done_one") if e.files == 1 else tr("st_done", n=e.files)
            icon, color = "check", c["ok"]
            tip = f"{pretty(e.folder)}\n{tr('open_result_tip')}" if e.folder else ""
        elif e.status == "error":
            text = tr(e.detail, **e.detail_args)
            icon, color = "alert", c["err"]
            tip = text
        elif e.status in ("decrypting", "extracting"):
            text = tr(f"st_{e.status}")
            icon, color = "clock", c["accent"]
        else:
            text = tr("st_pending")
            icon, color = "clock", c["muted"]
        item.setText(COL_STATUS, text)
        item.setIcon(COL_STATUS, theme.icon(icon, color, 18))
        item.setForeground(COL_STATUS, _brush(color))
        item.setToolTip(COL_STATUS, tip)

    def add_paths(self, paths: list[str]) -> None:
        if self.busy():
            return
        known = {e.path for e in self.entries}
        added = skipped = 0
        files: list[Path] = []
        for raw in paths:
            p = Path(raw)
            if p.is_dir():
                files.extend(sorted(q for q in p.rglob("*.age") if q.is_file()))
            else:
                files.append(p)
        for p in files:
            try:
                rp = p.resolve()
                st = rp.stat()
            except OSError:
                skipped += 1
                continue
            if rp in known or not rp.is_file() or not core.is_age_file(rp):
                skipped += 1
                continue
            known.add(rp)
            self.entries.append(Entry(path=rp, size=st.st_size, mtime=st.st_mtime))
            self.tree.addTopLevelItem(QTreeWidgetItem())
            self.refresh_row(len(self.entries) - 1)
            added += 1
        if skipped:
            self.set_status("status_skipped", {"n": added, "m": skipped})
        elif added:
            self.set_status("status_added", {"n": added})
        self.update_buttons()

    def pick_files(self) -> None:
        if self.busy():
            return
        paths, _ = QFileDialog.getOpenFileNames(self, tr("pick_title"), str(Path.home()), tr("pick_filter"))
        if paths:
            self.add_paths(paths)

    def remove_selected(self) -> None:
        if self.busy():
            return
        rows = sorted((self.tree.indexOfTopLevelItem(i) for i in self.tree.selectedItems()), reverse=True)
        for row in rows:
            self.tree.takeTopLevelItem(row)
            del self.entries[row]
        self.update_buttons()

    def clear_list(self) -> None:
        if self.busy():
            return
        self.tree.clear()
        self.entries.clear()
        self.set_status("status_ready")
        self.update_buttons()

    def _open_item(self, item: QTreeWidgetItem, _col: int) -> None:
        e = self.entries[self.tree.indexOfTopLevelItem(item)]
        if e.folder and e.folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(e.folder)))

    def open_destination(self) -> None:
        dest = destination()
        dest.mkdir(parents=True, exist_ok=True)
        os.chmod(dest, 0o700)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest)))

    # ── Clave ──

    def ask_key(self) -> bool:
        if self.busy():
            return False
        dialog = KeyDialog(self, self.colors, bool(self.identities))
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if accepted and dialog.identities:
            self.identities = dialog.identities
        elif dialog.forget:
            self.identities = None
            self.set_status("status_key_forgotten")
        self.update_chip()
        return accepted and bool(self.identities)

    # ── Exportar ──

    def export(self) -> None:
        if self.busy():
            return
        jobs = [(i, e.path) for i, e in enumerate(self.entries) if e.status in ("pending", "error")]
        if not jobs:
            self.set_status("status_nothing")
            return
        if not self.identities and not self.ask_key():
            return
        for i, _p in jobs:
            self.entries[i].status = "pending"
            self.refresh_row(i)
        self._total, self._finished = len(jobs), 0
        self.progress.setRange(0, self._total)
        self.progress.setValue(0)
        self.progress.show()

        self._thread = QThread(self)
        self._worker = ExportWorker(jobs, self.identities, destination())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.stage.connect(self._on_stage)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()
        self.update_buttons()

    @Slot(int, str)
    def _on_stage(self, index: int, stage: str) -> None:
        e = self.entries[index]
        e.status = stage
        self.refresh_row(index)
        self.set_status("status_working", {"i": self._finished + 1, "n": self._total, "name": e.path.name})

    @Slot(int, object)
    def _on_done(self, index: int, result: core.ExportResult) -> None:
        e = self.entries[index]
        e.status, e.folder, e.files, e.kind = "done", result.folder, result.files, result.kind
        self._step(index)

    @Slot(int, str, dict)
    def _on_failed(self, index: int, key: str, args: dict) -> None:
        e = self.entries[index]
        e.status, e.detail, e.detail_args = "error", key, args
        self._step(index)

    def _step(self, index: int) -> None:
        self._finished += 1
        self.progress.setValue(self._finished)
        self.refresh_row(index)

    @Slot()
    def _on_finished(self) -> None:
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread:
            thread.quit()
            thread.wait()
        self.progress.hide()
        ok = sum(1 for e in self.entries if e.status == "done")
        bad = sum(1 for e in self.entries if e.status == "error")
        self.set_status("status_done" if bad else "status_done_ok", {"ok": ok, "bad": bad})
        self.update_buttons()

    # ── Arrastrar y soltar ──

    def _set_drop_active(self, active: bool) -> None:
        self.drop.setProperty("active", "true" if active else "false")
        self.drop.style().unpolish(self.drop)
        self.drop.style().polish(self.drop)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and not self.busy():
            event.acceptProposedAction()
            self._set_drop_active(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_drop_active(False)

    def dropEvent(self, event) -> None:
        self._set_drop_active(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.add_paths(paths)

    def closeEvent(self, event) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
        self.identities = None
        super().closeEvent(event)


def _brush(color: str):
    from PySide6.QtGui import QBrush, QColor

    return QBrush(QColor(color))
