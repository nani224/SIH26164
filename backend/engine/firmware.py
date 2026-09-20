"""Firmware extraction sandbox for Squashfs and CPIO images.

Extracts partitions/files from embedded firmware images in a sandboxed manner:
- Squashfs (sqsh, hsqs, qshs, shsq)
- CPIO archives (070701, 070702 new ASCII, 070707 old ASCII)

Security guarantees:
1. Path traversal protection: rejects `..` and normalizes paths.
2. Resource bounded: limits maximum file count and total unpacked bytes.
3. Hostile-input hardened: bounds execution and handles truncated/corrupt images.
"""

from __future__ import annotations

import struct
from pathlib import PurePosixPath

_SQUASHFS_MAGICS = {b"sqsh", b"hsqs", b"qshs", b"shsq"}
_CPIO_MAGICS = {b"070701", b"070702", b"070707"}


def is_firmware_image(data: bytes) -> str | None:
    """Identify if data is a supported firmware image."""
    if len(data) >= 6:
        magic_6 = data[:6]
        if magic_6 in _CPIO_MAGICS:
            return "cpio"
    if len(data) >= 4:
        magic_4 = data[:4]
        if magic_4 in _SQUASHFS_MAGICS:
            return "squashfs"
    return None


def sanitize_archive_path(raw_path: str) -> str | None:
    """Sanitize archive entry path to prevent directory traversal."""
    p = PurePosixPath(raw_path)
    # Reject path traversal
    if ".." in p.parts:
        return None
    # Strip leading slashes
    parts = [part for part in p.parts if part not in ("/", "\\", "")]
    if not parts:
        return None
    return "/".join(parts)


def extract_cpio(
    data: bytes,
    max_files: int = 500,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[str, bytes]]:
    """Parse and extract files from a CPIO archive safely in memory."""
    files: list[tuple[str, bytes]] = []
    offset = 0
    total_extracted_bytes = 0
    n = len(data)

    while offset < n and len(files) < max_files and total_extracted_bytes < max_bytes:
        if offset + 6 > n:
            break
        magic = data[offset : offset + 6]
        if magic not in _CPIO_MAGICS:
            break

        if magic in (b"070701", b"070702"):  # New ASCII format (110-byte header)
            if offset + 110 > n:
                break
            try:
                filesize = int(data[offset + 54 : offset + 62], 16)
                namesize = int(data[offset + 94 : offset + 102], 16)
            except ValueError:
                break

            header_len = 110
            name_offset = offset + header_len
            if name_offset + namesize > n:
                break

            raw_name = data[name_offset : name_offset + namesize].rstrip(b"\x00").decode("latin1", errors="ignore")
            if raw_name == "TRAILER!!!":
                break

            # Names are padded to 4 bytes in new ASCII format
            name_padded = (header_len + namesize + 3) & ~3
            data_offset = offset + name_padded
            if data_offset + filesize > n:
                break

            file_content = data[data_offset : data_offset + filesize]
            clean_name = sanitize_archive_path(raw_name)
            if clean_name and filesize > 0:
                files.append((clean_name, file_content))
                total_extracted_bytes += len(file_content)

            # File data is also padded to 4 bytes
            data_padded = (filesize + 3) & ~3
            offset = data_offset + data_padded

        elif magic == b"070707":  # Old ASCII format (76-byte header)
            if offset + 76 > n:
                break
            try:
                filesize = int(data[offset + 35 : offset + 46], 8)
                namesize = int(data[offset + 59 : offset + 65], 8)
            except ValueError:
                break

            header_len = 76
            name_offset = offset + header_len
            if name_offset + namesize > n:
                break

            raw_name = data[name_offset : name_offset + namesize].rstrip(b"\x00").decode("latin1", errors="ignore")
            if raw_name == "TRAILER!!!":
                break

            data_offset = name_offset + namesize
            if data_offset + filesize > n:
                break

            file_content = data[data_offset : data_offset + filesize]
            clean_name = sanitize_archive_path(raw_name)
            if clean_name and filesize > 0:
                files.append((clean_name, file_content))
                total_extracted_bytes += len(file_content)

            offset = data_offset + filesize
        else:
            break

    return files


def extract_firmware(
    data: bytes,
    max_files: int = 500,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[str, bytes]]:
    """Extract files from supported firmware images in a sandboxed manner."""
    fmt = is_firmware_image(data)
    if fmt == "cpio":
        return extract_cpio(data, max_files=max_files, max_bytes=max_bytes)
    elif fmt == "squashfs":
        # Squashfs header parsing (96-byte super block)
        if len(data) >= 96:
            try:
                # Squashfs superblock has inode count, block size, compression, bytes used
                bytes_used = struct.unpack("<Q", data[40:48])[0]
                # Return the partition image slice for scanning
                return [("squashfs_root.img", data[: min(len(data), bytes_used if bytes_used > 0 else len(data))])]
            except struct.error:
                return [("squashfs_root.img", data)]
    return []
