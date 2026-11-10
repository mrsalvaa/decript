# SPDX-License-Identifier: GPL-3.0-or-later
"""Núcleo de decript: descifrar archivos age y extraerlos de forma segura.

No depende de la interfaz ni toca la red. La clave privada solo vive en memoria.
"""

from __future__ import annotations

import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pyrage

AGE_BINARY_MAGIC = b"age-encryption.org/v1"
AGE_ARMOR_MAGIC = b"-----BEGIN AGE ENCRYPTED FILE-----"
KEY_PREFIX = "AGE-SECRET-KEY-1"

# Sufijos de contenedor que se quitan del nombre de la carpeta de salida
_ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".tar.zst", ".tar", ".zip")


class DecriptError(Exception):
    """Error con un código estable (`code`) que la interfaz traduce."""

    code = "error"

    def __init__(self, detail: str = ""):
        super().__init__(detail or self.code)
        self.detail = detail


class NoKeyError(DecriptError):
    code = "no_key"  # el texto no contiene ninguna clave privada age


class InvalidKeyError(DecriptError):
    code = "invalid_key"  # hay una línea AGE-SECRET-KEY-1… pero no es válida


class NotAgeFileError(DecriptError):
    code = "not_age"  # el archivo no es un archivo age


class WrongKeyError(DecriptError):
    code = "wrong_key"  # la clave no corresponde a este archivo


class CorruptFileError(DecriptError):
    code = "corrupt"  # archivo age dañado o incompleto


class UnsafeArchiveError(DecriptError):
    code = "unsafe"  # el contenido intenta escribir fuera de su carpeta


class PassphraseFileError(DecriptError):
    code = "passphrase"  # cifrado con contraseña: todavía no soportado


@dataclass(frozen=True)
class ExportResult:
    source: Path
    folder: Path
    kind: str  # "tar", "zip" o "raw"
    files: int


# ── Clave privada ──────────────────────────────────────────────────────────────

def parse_identities(text: str) -> list:
    """Devuelve las identidades age que haya en `text` (contenido de un archivo de clave o texto pegado).

    Ignora comentarios y líneas vacías, como hace `age`.
    """
    identities = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith(KEY_PREFIX):
            try:
                identities.append(pyrage.x25519.Identity.from_str(line.upper()))
            except Exception as exc:  # pyrage.IdentityError u otros
                raise InvalidKeyError(str(exc)) from exc
    if not identities:
        raise NoKeyError()
    return identities


def load_identities_file(path: str | os.PathLike) -> list:
    p = Path(path)
    if p.stat().st_size > 1024 * 1024:  # un archivo de clave real pesa unos cientos de bytes
        raise NoKeyError("file too large")
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise NoKeyError("not text") from exc
    return parse_identities(text)


def public_keys(identities: list) -> list[str]:
    """Claves públicas (age1…) de las identidades, para mostrarlas sin revelar la privada."""
    return [str(i.to_public()) for i in identities]


# ── Archivos ───────────────────────────────────────────────────────────────────

def is_age_file(path: str | os.PathLike) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(64)
    except OSError:
        return False
    return head.startswith(AGE_BINARY_MAGIC) or head.lstrip().startswith(AGE_ARMOR_MAGIC)


def output_name(path: str | os.PathLike) -> str:
    """Nombre de la carpeta de salida: el del archivo sin `.age` ni la extensión de contenedor."""
    name = Path(path).name
    if name.lower().endswith(".age"):
        name = name[:-4]
    low = name.lower()
    for suffix in _ARCHIVE_SUFFIXES:
        if low.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
            break
    return name or "decript"


def inner_name(path: str | os.PathLike) -> str:
    """Nombre del archivo descifrado (el original sin `.age`)."""
    name = Path(path).name
    if name.lower().endswith(".age"):
        name = name[:-4]
    return name or "decrypted"


def guess_kind(path: str | os.PathLike) -> str:
    """Tipo esperado según el nombre (solo para mostrarlo en la lista)."""
    low = inner_name(path).lower()
    if low.endswith(".zip"):
        return "zip"
    if low.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
        return "tar"
    return "raw"


def _unique_dir(root: Path, name: str) -> Path:
    candidate = root / name
    n = 2
    while candidate.exists():
        candidate = root / f"{name}-{n}"
        n += 1
    return candidate


def _decrypt_to(src: Path, dst: Path, identities: list) -> None:
    if not is_age_file(src):
        raise NotAgeFileError(src.name)
    try:
        pyrage.decrypt_file(str(src), str(dst), identities)
    except pyrage.DecryptError as exc:
        msg = str(exc)
        low = msg.lower()
        if "no matching keys" in low:
            raise WrongKeyError(msg) from exc
        if "passphrase" in low or "scrypt" in low:
            raise PassphraseFileError(msg) from exc
        raise CorruptFileError(msg) from exc
    except OSError as exc:
        # pyrage informa así un archivo cortado o alterado a mitad del descifrado
        if "decryption error" in str(exc).lower():
            raise CorruptFileError(str(exc)) from exc
        raise


def _safe_extract_tar(archive: Path, dest: Path) -> int:
    count = 0
    try:
        with tarfile.open(archive) as tar:
            # filter="data": rechaza rutas absolutas, "..", enlaces que salen de la carpeta,
            # dispositivos, y quita setuid/permisos peligrosos.
            for member in tar:
                tar.extract(member, dest, filter="data")
                if member.isfile():
                    count += 1
    except tarfile.FilterError as exc:
        raise UnsafeArchiveError(str(exc)) from exc
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise CorruptFileError(str(exc)) from exc
    return count


def _safe_extract_zip(archive: Path, dest: Path) -> int:
    count = 0
    dest_resolved = dest.resolve()
    try:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                name = info.filename
                if name.startswith(("/", "\\")) or ".." in Path(name).parts or (len(name) > 1 and name[1] == ":"):
                    raise UnsafeArchiveError(name)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise UnsafeArchiveError(name)
                target = (dest / name).resolve()
                if target != dest_resolved and dest_resolved not in target.parents:
                    raise UnsafeArchiveError(name)
                zf.extract(info, dest)
                if not info.is_dir():
                    count += 1
    except zipfile.BadZipFile as exc:
        raise CorruptFileError(str(exc)) from exc
    return count


def _tighten_permissions(folder: Path) -> None:
    """Deja la carpeta exportada solo para el usuario (700 carpetas, 600 archivos)."""
    for base, dirs, files in os.walk(folder):
        os.chmod(base, 0o700)
        for name in files:
            p = os.path.join(base, name)
            if not os.path.islink(p):
                os.chmod(p, 0o600)


def export_file(
    source: str | os.PathLike,
    identities: list,
    dest_root: str | os.PathLike,
    on_stage: Callable[[str], None] | None = None,
) -> ExportResult:
    """Descifra `source` y lo deja extraído en una carpeta nueva dentro de `dest_root`.

    `on_stage` recibe "decrypting" y "extracting" para mostrar el progreso.
    Nunca pisa una carpeta existente: usa `nombre-2`, `nombre-3`, …
    Si algo falla, no deja restos.
    """
    src = Path(source)
    root = Path(dest_root)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)

    stage = on_stage or (lambda _s: None)

    # Carpeta de trabajo privada dentro del destino (mismo disco: mover es instantáneo)
    work = Path(tempfile.mkdtemp(prefix=".decript-", dir=root))
    try:
        stage("decrypting")
        plain = work / "plain"
        _decrypt_to(src, plain, identities)

        stage("extracting")
        content = work / "content"
        content.mkdir()
        if tarfile.is_tarfile(plain):
            kind = "tar"
            files = _safe_extract_tar(plain, content)
        elif zipfile.is_zipfile(plain):
            kind = "zip"
            files = _safe_extract_zip(plain, content)
        else:
            kind = "raw"
            shutil.move(str(plain), str(content / inner_name(src)))
            files = 1

        _tighten_permissions(content)
        final = _unique_dir(root, output_name(src))
        os.rename(content, final)
        return ExportResult(source=src, folder=final, kind=kind, files=files)
    finally:
        shutil.rmtree(work, ignore_errors=True)
