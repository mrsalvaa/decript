# SPDX-License-Identifier: GPL-3.0-or-later
import io
import os
import stat
import tarfile
import zipfile

import pyrage
import pytest

from decript import core


@pytest.fixture
def key():
    return pyrage.x25519.Identity.generate()


def enc(data: bytes, key) -> bytes:
    return pyrage.encrypt(data, [key.to_public()])


def make_tar(files: dict[str, bytes], gz=True, extra=None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz" if gz else "w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for info in extra or []:
            tar.addfile(info)
    return buf.getvalue()


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def leftovers(root):
    return [p.name for p in root.iterdir() if p.name.startswith(".decript-")]


# ── Clave ──────────────────────────────────────────────────────────────────────

def test_parse_key_file_format(key):
    text = f"# created: 2026-11-09T23:53:00-03:00\n# public key: {key.to_public()}\n{key}\n"
    ids = core.parse_identities(text)
    assert core.public_keys(ids) == [str(key.to_public())]


def test_parse_key_pasted_with_spaces_and_lowercase(key):
    ids = core.parse_identities(f"   {str(key).lower()}  \n")
    assert core.public_keys(ids) == [str(key.to_public())]


def test_parse_several_keys(key):
    other = pyrage.x25519.Identity.generate()
    assert len(core.parse_identities(f"{key}\n{other}\n")) == 2


@pytest.mark.parametrize("text", ["", "hola", "# solo un comentario\n", "age1qqqq\n"])
def test_no_key(text):
    with pytest.raises(core.NoKeyError):
        core.parse_identities(text)


def test_invalid_key():
    with pytest.raises(core.InvalidKeyError):
        core.parse_identities("AGE-SECRET-KEY-1NOESVALIDA")


def test_load_key_file_binary(tmp_path):
    p = tmp_path / "k"
    p.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(core.NoKeyError):
        core.load_identities_file(p)


# ── Nombres ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "name,expected",
    [
        ("radicale-10-11-2026_0031.tar.gz.age", "radicale-10-11-2026_0031"),
        ("vw-10-11-2026.tar.age", "vw-10-11-2026"),
        ("pihole-10-11-2026.zip.age", "pihole-10-11-2026"),
        ("notas.txt.age", "notas.txt"),
        ("COSA.TAR.GZ.AGE", "COSA"),
        ("sin-extension", "sin-extension"),
        (".tar.gz.age", ".tar.gz"),
    ],
)
def test_output_name(name, expected):
    assert core.output_name(name) == expected


def test_guess_kind():
    assert core.guess_kind("a.tar.gz.age") == "tar"
    assert core.guess_kind("a.zip.age") == "zip"
    assert core.guess_kind("a.txt.age") == "raw"


# ── Exportar ───────────────────────────────────────────────────────────────────

def test_export_tar_gz(tmp_path, key):
    src = tmp_path / "radicale-10-11-2026_0031.tar.gz.age"
    src.write_bytes(enc(make_tar({"radicale/config/users": b"u", "radicale/data/a.ics": b"ics"}), key))
    out = tmp_path / "decript"
    stages = []
    res = core.export_file(src, [key], out, stages.append)
    assert res.folder == out / "radicale-10-11-2026_0031"
    assert res.kind == "tar" and res.files == 2
    assert (res.folder / "radicale/data/a.ics").read_bytes() == b"ics"
    assert stages == ["decrypting", "extracting"]
    assert leftovers(out) == []


def test_export_plain_tar(tmp_path, key):
    src = tmp_path / "vw-10-11-2026.tar.age"
    src.write_bytes(enc(make_tar({"db.sqlite3": b"db"}, gz=False), key))
    res = core.export_file(src, [key], tmp_path / "out")
    assert (res.folder / "db.sqlite3").read_bytes() == b"db"


def test_export_zip(tmp_path, key):
    src = tmp_path / "pihole-10-11-2026.zip.age"
    src.write_bytes(enc(make_zip({"etc/pihole/pihole.toml": b"toml"}), key))
    res = core.export_file(src, [key], tmp_path / "out")
    assert res.kind == "zip" and res.files == 1
    assert (res.folder / "etc/pihole/pihole.toml").read_bytes() == b"toml"


def test_export_raw(tmp_path, key):
    src = tmp_path / "notas.txt.age"
    src.write_bytes(enc(b"hola", key))
    res = core.export_file(src, [key], tmp_path / "out")
    assert res.kind == "raw"
    assert (res.folder / "notas.txt").read_bytes() == b"hola"


def test_content_detected_not_by_name(tmp_path, key):
    src = tmp_path / "misterio.age"
    src.write_bytes(enc(make_zip({"a.txt": b"a"}), key))
    res = core.export_file(src, [key], tmp_path / "out")
    assert res.kind == "zip" and (res.folder / "a.txt").exists()


def test_never_overwrites(tmp_path, key):
    src = tmp_path / "x.tar.gz.age"
    src.write_bytes(enc(make_tar({"a": b"1"}), key))
    out = tmp_path / "out"
    r1 = core.export_file(src, [key], out)
    (r1.folder / "a").write_bytes(b"editado")
    r2 = core.export_file(src, [key], out)
    r3 = core.export_file(src, [key], out)
    assert [r.folder.name for r in (r1, r2, r3)] == ["x", "x-2", "x-3"]
    assert (r1.folder / "a").read_bytes() == b"editado"


def test_permissions(tmp_path, key):
    src = tmp_path / "x.tar.gz.age"
    src.write_bytes(enc(make_tar({"d/a": b"1"}), key))
    out = tmp_path / "out"
    res = core.export_file(src, [key], out)
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    assert stat.S_IMODE(res.folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((res.folder / "d").stat().st_mode) == 0o700
    assert stat.S_IMODE((res.folder / "d/a").stat().st_mode) == 0o600


def test_second_key_matches(tmp_path, key):
    other = pyrage.x25519.Identity.generate()
    src = tmp_path / "x.txt.age"
    src.write_bytes(enc(b"ok", key))
    res = core.export_file(src, [other, key], tmp_path / "out")
    assert (res.folder / "x.txt").read_bytes() == b"ok"


# ── Errores ────────────────────────────────────────────────────────────────────

def test_wrong_key(tmp_path, key):
    src = tmp_path / "x.tar.gz.age"
    src.write_bytes(enc(make_tar({"a": b"1"}), key))
    out = tmp_path / "out"
    with pytest.raises(core.WrongKeyError):
        core.export_file(src, [pyrage.x25519.Identity.generate()], out)
    assert list(out.iterdir()) == []


def test_not_age(tmp_path, key):
    src = tmp_path / "x.tar.gz.age"
    src.write_bytes(make_tar({"a": b"1"}))
    with pytest.raises(core.NotAgeFileError):
        core.export_file(src, [key], tmp_path / "out")


def test_empty_file(tmp_path, key):
    src = tmp_path / "vacio.tar.gz.age"
    src.write_bytes(b"")
    with pytest.raises(core.NotAgeFileError):
        core.export_file(src, [key], tmp_path / "out")


def test_truncated(tmp_path, key):
    data = enc(make_tar({"a": os.urandom(200_000)}), key)
    src = tmp_path / "x.tar.gz.age"
    src.write_bytes(data[: len(data) // 2])
    out = tmp_path / "out"
    with pytest.raises(core.CorruptFileError):
        core.export_file(src, [key], out)
    assert list(out.iterdir()) == []


def test_passphrase_file(tmp_path, key):
    src = tmp_path / "x.txt.age"
    src.write_bytes(pyrage.passphrase.encrypt(b"hola", "secreta"))
    with pytest.raises((core.PassphraseFileError, core.WrongKeyError)):
        core.export_file(src, [key], tmp_path / "out")


def test_tar_path_traversal(tmp_path, key):
    src = tmp_path / "malo.tar.gz.age"
    src.write_bytes(enc(make_tar({"../../fuera.txt": b"x"}), key))
    out = tmp_path / "a" / "b" / "out"
    with pytest.raises(core.UnsafeArchiveError):
        core.export_file(src, [key], out)
    assert not (tmp_path / "a" / "fuera.txt").exists() and not (tmp_path / "fuera.txt").exists()
    assert list(out.iterdir()) == []


def test_tar_absolute_symlink(tmp_path, key):
    link = tarfile.TarInfo("enlace")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    src = tmp_path / "malo.tar.gz.age"
    src.write_bytes(enc(make_tar({"a": b"1"}, extra=[link]), key))
    with pytest.raises(core.UnsafeArchiveError):
        core.export_file(src, [key], tmp_path / "out")


def test_zip_path_traversal(tmp_path, key):
    src = tmp_path / "malo.zip.age"
    src.write_bytes(enc(make_zip({"../fuera.txt": b"x"}), key))
    out = tmp_path / "a" / "out"
    with pytest.raises(core.UnsafeArchiveError):
        core.export_file(src, [key], out)
    assert not (tmp_path / "a" / "fuera.txt").exists()


def test_is_age_file(tmp_path, key):
    good = tmp_path / "g.age"
    good.write_bytes(enc(b"x", key))
    bad = tmp_path / "b.age"
    bad.write_bytes(b"PK\x03\x04")
    assert core.is_age_file(good) and not core.is_age_file(bad)
    assert not core.is_age_file(tmp_path / "no-existe")
