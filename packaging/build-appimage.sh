#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Construye dist/decript-<versión>-x86_64.AppImage
# Requisitos: uv y appimagetool (en el PATH, o su AppImage en build/appimagetool-x86_64.AppImage).
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
[ -x "$PY" ] || uv venv -q --python 3.13 .venv
uv pip install -q --python "$PY" pyrage PySide6-Essentials pyinstaller

VERSION=$("$PY" -c "import sys; sys.path.insert(0,'src'); import decript; print(decript.__version__)")
rm -rf build/pyi build/launcher.py build/decript.spec dist/decript AppDir
mkdir -p build dist

# 1) Empaquetar Python + Qt + pyrage en una carpeta autónoma
printf 'import sys\nfrom decript.__main__ import main\nsys.exit(main())\n' > build/launcher.py
"$PY" -m PyInstaller --noconfirm --clean --windowed --name decript \
  --paths src --distpath dist --workpath build/pyi --specpath build \
  --exclude-module tkinter --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtQml \
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtOpenGL --exclude-module PySide6.QtPdf \
  build/launcher.py >build/pyinstaller.log 2>&1 || { tail -20 build/pyinstaller.log; exit 1; }

# Quitar plugins de Qt y bibliotecas del sistema que la app no usa
"$PY" packaging/prune.py dist/decript/_internal

# 2) Armar el AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
cp -a dist/decript AppDir/usr/lib-decript
ln -s ../lib-decript/decript AppDir/usr/bin/decript
cp packaging/decript.desktop AppDir/usr/share/applications/decript.desktop
cp packaging/decript.desktop AppDir/decript.desktop
QT_QPA_PLATFORM=offscreen PYTHONPATH=src "$PY" packaging/make_icon.py AppDir/usr/share/icons/hicolor/256x256/apps/decript.png 256
cp AppDir/usr/share/icons/hicolor/256x256/apps/decript.png AppDir/decript.png
ln -s decript.png AppDir/.DirIcon
cp LICENSE AppDir/usr/lib-decript/LICENSE
printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/lib-decript/decript" "$@"\n' > AppDir/AppRun
chmod +x AppDir/AppRun
echo "AppDir listo: $(du -sh AppDir | cut -f1)"

# 3) Crear el AppImage
if command -v appimagetool >/dev/null; then
  TOOL=(appimagetool)
elif [ -x build/appimagetool-x86_64.AppImage ]; then
  TOOL=(build/appimagetool-x86_64.AppImage --appimage-extract-and-run)
else
  echo "Falta appimagetool: instalalo, o dejá su AppImage en build/appimagetool-x86_64.AppImage" >&2
  echo "  https://github.com/AppImage/appimagetool/releases" >&2
  exit 2
fi
OUT="dist/decript-$VERSION-x86_64.AppImage"
ARCH=x86_64 "${TOOL[@]}" --no-appstream AppDir "$OUT" >build/appimagetool.log 2>&1 || { tail -20 build/appimagetool.log; exit 1; }
chmod +x "$OUT"
ls -lh "$OUT"
