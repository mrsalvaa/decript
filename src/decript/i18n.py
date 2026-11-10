# SPDX-License-Identifier: GPL-3.0-or-later
"""Textos de la interfaz en español e inglés (sin dependencias ni archivos externos)."""

from __future__ import annotations

import locale
import os

LANGS = ("es", "en")

_T: dict[str, dict[str, str]] = {
    # Barra
    "add": {"es": "Agregar", "en": "Add"},
    "add_tip": {"es": "Agregar archivos .age (Ctrl+O)", "en": "Add .age files (Ctrl+O)"},
    "remove": {"es": "Quitar", "en": "Remove"},
    "remove_tip": {"es": "Quitar de la lista los archivos seleccionados (Supr)", "en": "Remove the selected files from the list (Del)"},
    "clear": {"es": "Vaciar", "en": "Clear"},
    "clear_tip": {"es": "Vaciar la lista", "en": "Clear the list"},
    "key": {"es": "Clave privada", "en": "Private key"},
    "key_tip": {"es": "Cargar la clave privada de age (Ctrl+K)", "en": "Load the age private key (Ctrl+K)"},
    "export": {"es": "Exportar", "en": "Export"},
    "export_tip": {"es": "Descifrar y extraer en {dest} (Ctrl+E)", "en": "Decrypt and unpack into {dest} (Ctrl+E)"},
    "open_folder": {"es": "Abrir carpeta", "en": "Open folder"},
    "open_folder_tip": {"es": "Abrir {dest}", "en": "Open {dest}"},
    "lang_tip": {"es": "Idioma: español. Clic para cambiar a inglés", "en": "Language: English. Click to switch to Spanish"},
    # Lista
    "col_file": {"es": "Archivo", "en": "File"},
    "col_type": {"es": "Contenido", "en": "Content"},
    "col_size": {"es": "Tamaño", "en": "Size"},
    "col_date": {"es": "Fecha", "en": "Date"},
    "col_status": {"es": "Estado", "en": "Status"},
    "kind_tar": {"es": "Archivo tar", "en": "Tar archive"},
    "kind_zip": {"es": "Archivo zip", "en": "Zip archive"},
    "kind_raw": {"es": "Archivo suelto", "en": "Single file"},
    "st_pending": {"es": "Pendiente", "en": "Pending"},
    "st_decrypting": {"es": "Descifrando…", "en": "Decrypting…"},
    "st_extracting": {"es": "Extrayendo…", "en": "Unpacking…"},
    "st_done": {"es": "Listo · {n} archivos", "en": "Done · {n} files"},
    "st_done_one": {"es": "Listo · 1 archivo", "en": "Done · 1 file"},
    "empty_title": {"es": "Arrastrá acá tus archivos .age", "en": "Drop your .age files here"},
    "empty_sub": {
        "es": "o usá Agregar. Después cargá tu clave privada y tocá Exportar.",
        "en": "or use Add. Then load your private key and press Export.",
    },
    # Clave
    "key_none": {"es": "Sin clave", "en": "No key"},
    "key_loaded": {"es": "Clave cargada · {pub}", "en": "Key loaded · {pub}"},
    "key_title": {"es": "Clave privada de age", "en": "age private key"},
    "key_intro": {
        "es": "Elegí el archivo de tu clave o pegá la línea que empieza con AGE-SECRET-KEY-1. "
              "La clave queda solo en memoria y se olvida al cerrar la app.",
        "en": "Choose your key file or paste the line starting with AGE-SECRET-KEY-1. "
              "The key is kept in memory only and forgotten when the app closes.",
    },
    "key_choose": {"es": "Elegir archivo…", "en": "Choose file…"},
    "key_paste_ph": {"es": "o pegá acá: AGE-SECRET-KEY-1…", "en": "or paste here: AGE-SECRET-KEY-1…"},
    "key_show": {"es": "Mostrar", "en": "Show"},
    "key_hide": {"es": "Ocultar", "en": "Hide"},
    "key_use": {"es": "Usar esta clave", "en": "Use this key"},
    "key_forget": {"es": "Olvidar clave", "en": "Forget key"},
    "key_ok": {"es": "Clave válida. Su clave pública es:", "en": "Valid key. Its public key is:"},
    "key_ok_many": {"es": "{n} claves válidas. Claves públicas:", "en": "{n} valid keys. Public keys:"},
    "key_file_filter": {"es": "Claves de age (*.txt *.key *.age-key);;Todos los archivos (*)", "en": "age keys (*.txt *.key *.age-key);;All files (*)"},
    "cancel": {"es": "Cancelar", "en": "Cancel"},
    # Diálogos y estado
    "pick_title": {"es": "Agregar archivos cifrados", "en": "Add encrypted files"},
    "pick_filter": {"es": "Archivos age (*.age);;Todos los archivos (*)", "en": "age files (*.age);;All files (*)"},
    "status_ready": {"es": "Destino: {dest}", "en": "Destination: {dest}"},
    "status_working": {"es": "Exportando {i} de {n}: {name}", "en": "Exporting {i} of {n}: {name}"},
    "status_done": {"es": "Exportación terminada: {ok} listos, {bad} con error. Carpeta: {dest}", "en": "Export finished: {ok} done, {bad} failed. Folder: {dest}"},
    "status_done_ok": {"es": "Exportación terminada: {ok} listos en {dest}", "en": "Export finished: {ok} done in {dest}"},
    "status_nothing": {"es": "No hay archivos pendientes para exportar.", "en": "There are no pending files to export."},
    "status_added": {"es": "{n} agregados", "en": "{n} added"},
    "status_skipped": {"es": "{n} agregados, {m} omitidos (repetidos o no son archivos age)", "en": "{n} added, {m} skipped (duplicates or not age files)"},
    "status_key_forgotten": {"es": "Clave olvidada.", "en": "Key forgotten."},
    "open_result_tip": {"es": "Doble clic para abrir la carpeta", "en": "Double-click to open the folder"},
    # Errores
    "err_no_key": {"es": "No encontré ninguna clave privada (una línea que empiece con AGE-SECRET-KEY-1).", "en": "No private key found (a line starting with AGE-SECRET-KEY-1)."},
    "err_invalid_key": {"es": "La clave está incompleta o mal copiada.", "en": "The key is incomplete or was copied incorrectly."},
    "err_not_age": {"es": "No es un archivo age", "en": "Not an age file"},
    "err_wrong_key": {"es": "La clave no corresponde a este archivo", "en": "The key does not match this file"},
    "err_corrupt": {"es": "Archivo dañado o incompleto", "en": "Damaged or incomplete file"},
    "err_unsafe": {"es": "Contenido inseguro: intenta escribir fuera de su carpeta", "en": "Unsafe content: it tries to write outside its folder"},
    "err_passphrase": {"es": "Cifrado con contraseña (todavía no soportado)", "en": "Passphrase-encrypted (not supported yet)"},
    "err_missing": {"es": "El archivo ya no existe", "en": "The file no longer exists"},
    "err_io": {"es": "No se pudo escribir: {detail}", "en": "Could not write: {detail}"},
    "err_error": {"es": "Error: {detail}", "en": "Error: {detail}"},
    "err_read_key": {"es": "No se pudo leer el archivo: {detail}", "en": "Could not read the file: {detail}"},
}

_lang = "en"


def system_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return "es" if value.lower().startswith("es") else "en"
    try:
        code = locale.getlocale()[0] or ""
    except ValueError:
        code = ""
    return "es" if code.lower().startswith("es") else "en"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else "en"


def language() -> str:
    return _lang


def tr(key: str, **kwargs) -> str:
    text = _T[key][_lang]
    return text.format(**kwargs) if kwargs else text


def human_size(n: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            text = f"{size:.1f}"
            if _lang == "es":
                text = text.replace(".", ",")
            return f"{text} {unit}"
        size /= 1024
    return str(n)
