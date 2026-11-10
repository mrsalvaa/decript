# SPDX-License-Identifier: GPL-3.0-or-later
"""Genera las capturas del README con datos inventados (nunca con backups reales).

Uso: QT_QPA_PLATFORM=offscreen python tools/screenshots.py <carpeta de salida>
"""

import io
import os
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pyrage

work = Path(tempfile.mkdtemp(prefix="decript-demo-"))
os.environ["DECRIPT_DEST"] = str(work / "decript")
os.environ["HOME"] = str(work)

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from decript import i18n, theme  # noqa: E402
from decript.ui import KeyDialog, MainWindow  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
key = pyrage.x25519.Identity.generate()
other = pyrage.x25519.Identity.generate()


def tar_gz(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def zipped(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


samples = work / "samples"
samples.mkdir()
demo = {
    "photos-2026-01-15.tar.gz.age": (tar_gz({f"photos/img_{i:03}.jpg": os.urandom(40_000) for i in range(48)}), key),
    "documents-2026-01-15.tar.gz.age": (tar_gz({f"docs/report_{i}.odt": os.urandom(9_000) for i in range(12)}), key),
    "calendar-2026-01-15.tar.age": (tar_gz({f"cal/event_{i}.ics": b"BEGIN:VCALENDAR" for i in range(230)}), key),
    "router-config.zip.age": (zipped({"config/settings.toml": b"name = 'demo'", "config/hosts": b"127.0.0.1 localhost"}), key),
    "notes.txt.age": (b"Just a note.\n", key),
    "old-laptop-2024.tar.gz.age": (tar_gz({"a.txt": b"x"}), other),
}
for name, (data, k) in demo.items():
    (samples / name).write_bytes(pyrage.encrypt(data, [k.to_public()]))


def wait(ms=150):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setWindowIcon(theme.app_icon())

for lang in ("en", "es"):
    for mode in ("light", "dark"):
        os.environ["DECRIPT_THEME"] = mode
        i18n.set_language(lang)
        w = MainWindow()
        w.resize(1000, 600)
        w.show()
        wait()
        w.grab().save(str(out / f"empty-{mode}-{lang}.png"))
        w.add_paths(sorted(str(p) for p in samples.iterdir()))
        w.identities = [key]
        w.update_chip()
        wait()
        w.grab().save(str(out / f"list-{mode}-{lang}.png"))
        w.export()
        while w.busy():
            wait(50)
        wait()
        w.grab().save(str(out / f"done-{mode}-{lang}.png"))
        d = KeyDialog(w, w.colors, False)
        d.edit.setText(str(key))
        d.show()
        wait()
        d.grab().save(str(out / f"key-{mode}-{lang}.png"))
        d.close()
        w.close()
print("ok", sorted(p.name for p in out.iterdir()))
