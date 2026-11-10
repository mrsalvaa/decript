# SPDX-License-Identifier: GPL-3.0-or-later
"""Quita del paquete los plugins de Qt que decript no usa y las bibliotecas que solo ellos necesitaban.

Uso: python prune.py <carpeta _internal>
"""
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
plugins = root / "PySide6" / "Qt" / "plugins"

# 1) Plugins innecesarios (la app usa el estilo Fusion, solo SVG/PNG y ventanas Wayland/X11)
unwanted = [
    "platformthemes/libqgtk3.so",
    "platforms/libqeglfs.so", "platforms/libqlinuxfb.so", "platforms/libqminimalegl.so",
    "platforms/libqvkkhrdisplay.so", "platforms/libqvnc.so",
    "imageformats/libqgif.so", "imageformats/libqicns.so", "imageformats/libqico.so", "imageformats/libqjpeg.so",
    "imageformats/libqtga.so", "imageformats/libqtiff.so", "imageformats/libqwbmp.so", "imageformats/libqwebp.so",
    "egldeviceintegrations", "generic",
]
for rel in unwanted:
    p = plugins / rel
    if p.is_dir():
        for f in sorted(p.rglob("*"), reverse=True):
            f.unlink() if f.is_file() or f.is_symlink() else f.rmdir()
        p.rmdir()
    elif p.exists():
        p.unlink()

# 2) Bibliotecas sueltas que ya nadie necesita
top = {p.name: p for p in root.iterdir() if p.is_file() and ".so" in p.name}
keep_always = {n for n in top if n.startswith(("libpython", "libcrypto", "libssl", "libffi", "libmpdec", "libsqlite3", "libz", "liblzma", "libbz2", "libexpat"))}
needed: set[str] = set(keep_always)
elfs = [p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and (".so" in p.name) and p.parent != root]
elfs += [root.parent / "decript"]
queue = list(elfs)
seen: set[Path] = set()
while queue:
    f = queue.pop()
    if f in seen:
        continue
    seen.add(f)
    out = subprocess.run(["objdump", "-p", str(f)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "NEEDED" and parts[1] in top and parts[1] not in needed:
            needed.add(parts[1])
            queue.append(top[parts[1]])
    if f.parent == root:
        continue
for name in keep_always:
    queue.append(top[name])
while queue:
    f = queue.pop()
    if f in seen:
        continue
    seen.add(f)
    out = subprocess.run(["objdump", "-p", str(f)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "NEEDED" and parts[1] in top and parts[1] not in needed:
            needed.add(parts[1])
            queue.append(top[parts[1]])

removed = 0
for name, path in top.items():
    if name not in needed:
        path.unlink()
        removed += 1
print(f"prune: {removed} bibliotecas quitadas, {len(needed)} conservadas")
