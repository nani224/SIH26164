"""Sandboxed archive ingestion with Zip-Slip, symlink traversal, and decompression bomb protection.

Phase 6: Provides safe streaming ingest of archives (.zip, .tar, .tar.gz, .tgz) into
an isolated sandbox directory, calculating the bundle SHA-256 on the fly.
"""

from __future__ import annotations

import hashlib
import os
import tarfile
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import BinaryIO

# Security limits per brief and ADRs
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB upload cap
MAX_UNCOMPRESSED_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB uncompressed cap
MAX_FILE_COUNT = 50_000  # Max files allowed in archive
MAX_COMPRESSION_RATIO = 100.0  # Max expansion ratio (ratio defense)
CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer


class IngestError(Exception):
    """Base exception for ingestion and extraction errors."""


class ArchiveSizeLimitExceeded(IngestError):
    """Uploaded archive exceeds size limits."""


class ZipSlipError(IngestError):
    """Archive contains path traversal attempts (e.g. '../')."""


class SymlinkTraversalError(IngestError):
    """Archive contains malicious symlinks pointing outside sandbox."""


class DecompressionBombError(IngestError):
    """Archive exceeds uncompressed size or file count limits."""


class InvalidArchiveError(IngestError):
    """Uploaded file is not a supported or valid archive."""


def compute_stream_hash_and_save(
    stream: BinaryIO,
    dest_path: Path,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> tuple[str, int]:
    """Reads a synchronous binary stream, writes to dest_path, and computes SHA-256."""
    hasher = hashlib.sha256()
    total_bytes = 0
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with dest_path.open("wb") as out_f:
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                out_f.close()
                dest_path.unlink(missing_ok=True)
                raise ArchiveSizeLimitExceeded(f"Upload exceeded maximum allowed size of {max_bytes} bytes")
            hasher.update(chunk)
            out_f.write(chunk)

    return hasher.hexdigest(), total_bytes


async def async_compute_stream_hash_and_save(
    stream: AsyncIterator[bytes],
    dest_path: Path,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> tuple[str, int]:
    """Reads an async chunk generator, writes to dest_path, and computes SHA-256."""
    hasher = hashlib.sha256()
    total_bytes = 0
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with dest_path.open("wb") as out_f:
        async for chunk in stream:
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                out_f.close()
                dest_path.unlink(missing_ok=True)
                raise ArchiveSizeLimitExceeded(f"Upload exceeded maximum allowed size of {max_bytes} bytes")
            hasher.update(chunk)
            out_f.write(chunk)

    return hasher.hexdigest(), total_bytes


def _is_suspicious_path(name: str) -> bool:
    """Checks for obvious path traversal characters."""
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../"):
        return True
    parts = normalized.split("/")
    if ".." in parts:
        return True
    return len(parts) > 0 and ":" in parts[0]


def safe_extract_archive(archive_path: Path | str, target_dir: Path | str) -> tuple[int, int]:
    """Safely extracts an archive (.zip or .tar.*) into target_dir.

    Enforces:
    - Path traversal (Zip-Slip) defense
    - Symlink escape defense
    - File count and uncompressed size quotas

    Returns (file_count, total_uncompressed_bytes).
    """
    archive_path = Path(archive_path).resolve()
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if not archive_path.is_file():
        raise InvalidArchiveError(f"Archive file not found: {archive_path}")

    # Check zip format first
    if zipfile.is_zipfile(archive_path):
        return _extract_zip(archive_path, target_dir)

    # Check tar formats
    if tarfile.is_tarfile(archive_path):
        return _extract_tar(archive_path, target_dir)

    raise InvalidArchiveError("Unsupported archive format. Expected .zip, .tar, .tar.gz, or .tgz")


def _extract_zip(archive_path: Path, target_dir: Path) -> tuple[int, int]:
    file_count = 0
    total_uncompressed = 0
    target_root_str = str(target_dir)

    with zipfile.ZipFile(archive_path, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) > MAX_FILE_COUNT:
            msg = f"Archive exceeds maximum file count limit ({len(infolist)} > {MAX_FILE_COUNT})"
            raise DecompressionBombError(msg)

        for info in infolist:
            file_count += 1
            if file_count > MAX_FILE_COUNT:
                raise DecompressionBombError(f"Archive exceeds maximum file count limit ({MAX_FILE_COUNT})")

            total_uncompressed += info.file_size
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise DecompressionBombError(
                    f"Archive exceeds uncompressed size limit ({total_uncompressed} > {MAX_UNCOMPRESSED_BYTES})"
                )

            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                ratio = info.file_size / info.compress_size
                raise DecompressionBombError(
                    f"Zip entry {info.filename!r} exceeds max compression ratio "
                    f"({ratio:.1f}x > {MAX_COMPRESSION_RATIO}x)"
                )

            if _is_suspicious_path(info.filename):
                raise ZipSlipError(f"Suspicious path in zip archive: {info.filename}")

            dest = (target_dir / info.filename).resolve()
            dest_str = str(dest)
            if not (dest_str == target_root_str or dest_str.startswith(target_root_str + os.sep)):
                raise ZipSlipError(f"Path traversal detected in zip archive: {info.filename}")

            # Check for symlink entries in zip (unix permission mode 0o120000)
            is_symlink = (info.external_attr >> 16) & 0o120000 == 0o120000
            if is_symlink:
                link_target = zf.read(info).decode("utf-8", errors="replace")
                if _is_suspicious_path(link_target):
                    raise SymlinkTraversalError(f"Malicious symlink in zip: {info.filename} -> {link_target}")
                resolved_link = (dest.parent / link_target).resolve()
                resolved_str = str(resolved_link)
                if not (resolved_str == target_root_str or resolved_str.startswith(target_root_str + os.sep)):
                    err_msg = f"Symlink points outside target sandbox: {info.filename} -> {link_target}"
                    raise SymlinkTraversalError(err_msg)

        # All entries passed pre-inspection; safely extract
        zf.extractall(target_dir)

    return file_count, total_uncompressed


def _extract_tar(archive_path: Path, target_dir: Path) -> tuple[int, int]:
    file_count = 0
    total_uncompressed = 0
    target_root_str = str(target_dir)
    # tar's compression (gzip) wraps the whole stream, not each member, so
    # there's no per-entry compressed size the way zip has -- the ratio
    # bomb defense here is aggregate: the archive's own on-disk (compressed)
    # size vs. everything it claims to expand to.
    compressed_size = archive_path.stat().st_size

    with tarfile.open(archive_path, "r:*") as tf:
        members = tf.getmembers()
        if len(members) > MAX_FILE_COUNT:
            msg = f"Archive exceeds maximum file count limit ({len(members)} > {MAX_FILE_COUNT})"
            raise DecompressionBombError(msg)

        for member in members:
            file_count += 1
            if file_count > MAX_FILE_COUNT:
                raise DecompressionBombError(f"Archive exceeds maximum file count limit ({MAX_FILE_COUNT})")

            total_uncompressed += member.size
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise DecompressionBombError(
                    f"Archive exceeds uncompressed size limit ({total_uncompressed} > {MAX_UNCOMPRESSED_BYTES})"
                )

            if compressed_size > 0 and total_uncompressed / compressed_size > MAX_COMPRESSION_RATIO:
                ratio = total_uncompressed / compressed_size
                raise DecompressionBombError(
                    f"Archive exceeds max compression ratio ({ratio:.1f}x > {MAX_COMPRESSION_RATIO}x)"
                )

            if _is_suspicious_path(member.name):
                raise ZipSlipError(f"Suspicious path in tar archive: {member.name}")

            dest = (target_dir / member.name).resolve()
            dest_str = str(dest)
            if not (dest_str == target_root_str or dest_str.startswith(target_root_str + os.sep)):
                raise ZipSlipError(f"Path traversal detected in tar archive: {member.name}")

            if member.issym() or member.islnk():
                link_target = member.linkname
                if _is_suspicious_path(link_target):
                    raise SymlinkTraversalError(f"Malicious symlink in tar: {member.name} -> {link_target}")
                resolved_link = (dest.parent / link_target).resolve()
                resolved_str = str(resolved_link)
                if not (resolved_str == target_root_str or resolved_str.startswith(target_root_str + os.sep)):
                    err_msg = f"Symlink points outside target sandbox: {member.name} -> {link_target}"
                    raise SymlinkTraversalError(err_msg)

        # filter="data" (Python 3.12+): rejects device files/absolute
        # links and strips ownership metadata on extraction, on top of
        # the manual path/symlink checks already done above -- adopting
        # the safer default now silences tarfile's own deprecation
        # warning about the pending 3.14 behavior change.
        tf.extractall(target_dir, filter="data")

    return file_count, total_uncompressed
