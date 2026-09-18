"""Tests for Phase 6 sandboxed streaming ingest and archive protection."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from engine.ingest import (
    ArchiveSizeLimitExceeded,
    DecompressionBombError,
    InvalidArchiveError,
    SymlinkTraversalError,
    ZipSlipError,
    compute_stream_hash_and_save,
    safe_extract_archive,
)


def test_safe_extract_valid_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("hello.txt", "hello world")
        zf.writestr("sub/nested.py", "import hashlib\nhashlib.sha256(b'test')")

    target_dir = tmp_path / "extracted"
    count, total_bytes = safe_extract_archive(zip_path, target_dir)

    assert count == 2
    assert (target_dir / "hello.txt").read_text() == "hello world"
    assert (target_dir / "sub" / "nested.py").exists()


def test_safe_extract_valid_tar_gz(tmp_path: Path) -> None:
    tar_path = tmp_path / "valid.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        data = b"print('secure test')"
        ti = tarfile.TarInfo(name="main.py")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))

    target_dir = tmp_path / "extracted_tar"
    count, total_bytes = safe_extract_archive(tar_path, target_dir)

    assert count == 1
    assert (target_dir / "main.py").read_bytes() == data


def test_zip_slip_rejection(tmp_path: Path) -> None:
    bad_zip = tmp_path / "zipslip.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("../../escaped.txt", "evil")

    target_dir = tmp_path / "sandbox"
    with pytest.raises(ZipSlipError):
        safe_extract_archive(bad_zip, target_dir)

    assert not (tmp_path / "escaped.txt").exists()


def test_tar_slip_rejection(tmp_path: Path) -> None:
    bad_tar = tmp_path / "tarslip.tar"
    with tarfile.open(bad_tar, "w") as tf:
        data = b"malicious content"
        ti = tarfile.TarInfo(name="../escape.txt")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))

    target_dir = tmp_path / "sandbox"
    with pytest.raises(ZipSlipError):
        safe_extract_archive(bad_tar, target_dir)


def test_tar_symlink_traversal_rejection(tmp_path: Path) -> None:
    bad_tar = tmp_path / "symlink_evil.tar"
    with tarfile.open(bad_tar, "w") as tf:
        ti = tarfile.TarInfo(name="evil_link")
        ti.type = tarfile.SYMTYPE
        ti.linkname = "../../outside"
        tf.addfile(ti)

    target_dir = tmp_path / "sandbox"
    with pytest.raises(SymlinkTraversalError):
        safe_extract_archive(bad_tar, target_dir)


def test_invalid_archive_rejection(tmp_path: Path) -> None:
    corrupt_file = tmp_path / "corrupt.dat"
    corrupt_file.write_bytes(b"not a real archive header")

    target_dir = tmp_path / "sandbox"
    with pytest.raises(InvalidArchiveError):
        safe_extract_archive(corrupt_file, target_dir)


def test_decompression_bomb_file_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import engine.ingest

    monkeypatch.setattr(engine.ingest, "MAX_FILE_COUNT", 5)

    bomb_zip = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb_zip, "w") as zf:
        for i in range(10):
            zf.writestr(f"file_{i}.txt", f"data_{i}")

    target_dir = tmp_path / "sandbox"
    with pytest.raises(DecompressionBombError):
        safe_extract_archive(bomb_zip, target_dir)


def test_stream_hash_and_size_limit(tmp_path: Path) -> None:
    data = b"deterministic stream data for hashing"
    stream = io.BytesIO(data)
    dest_path = tmp_path / "saved.bin"

    sha256, total_bytes = compute_stream_hash_and_save(stream, dest_path, max_bytes=100)
    assert total_bytes == len(data)
    assert dest_path.read_bytes() == data

    # Test size limit breach
    stream_large = io.BytesIO(b"X" * 200)
    dest_path_large = tmp_path / "large.bin"
    with pytest.raises(ArchiveSizeLimitExceeded):
        compute_stream_hash_and_save(stream_large, dest_path_large, max_bytes=50)
    assert not dest_path_large.exists()
