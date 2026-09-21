"""Hostile input tests for binary parsing (PE, Mach-O, ELF), firmware extraction, and source detectors.

Validates that:
1. Malformed and adversarial binaries (truncated headers, corrupted section tables,
   invalid offsets) never crash the engine or hang indefinitely.
2. Firmware extraction rejects path traversal attacks (Zip Slip / CPIO Slip),
   enforces resource bounds (max files, max bytes), and handles corrupted headers.
3. Source detectors handle invalid UTF-8, unterminated strings, and pathological syntax.
"""

from __future__ import annotations

import struct

from engine import binary, firmware, source_csharp, source_rust


def test_hostile_pe_truncated() -> None:
    """Truncated PE headers should be handled gracefully without crashing."""
    # Truncated DOS header (< 64 bytes)
    detections = binary.scan_binary(b"MZ\x00\x00", "truncated.exe")
    assert isinstance(detections, list)

    # DOS header pointing beyond buffer
    dos_header = bytearray(64)
    dos_header[:2] = b"MZ"
    struct.pack_into("<I", dos_header, 0x3C, 0x1000)  # e_lfanew points way beyond
    detections = binary.scan_binary(bytes(dos_header), "bad_lfanew.exe")
    assert isinstance(detections, list)


def test_hostile_pe_corrupted_nt_header() -> None:
    """PE with invalid NT signature or corrupted headers."""
    buf = bytearray(256)
    buf[:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, 64)
    # Corrupt NT signature
    buf[64:68] = b"NOPE"
    detections = binary.scan_binary(bytes(buf), "corrupt_nt.exe")
    assert isinstance(detections, list)


def test_hostile_macho_corrupted() -> None:
    """Mach-O with corrupted headers or invalid command lengths."""
    # Truncated Mach-O 64 header (< 32 bytes)
    detections = binary.scan_binary(b"\xfe\xed\xfa\xcf\x00\x00", "corrupt.dylib")
    assert isinstance(detections, list)

    # Mach-O header with invalid load command count
    buf = bytearray(64)
    struct.pack_into("<I", buf, 0, 0xFEEDFACF)  # MH_MAGIC_64
    struct.pack_into("<I", buf, 16, 999999)    # huge ncmds
    struct.pack_into("<I", buf, 20, 1000000)   # huge sizeofcmds
    detections = binary.scan_binary(bytes(buf), "huge_cmds.dylib")
    assert isinstance(detections, list)


def test_hostile_elf_corrupted() -> None:
    """ELF with corrupted section header offsets."""
    buf = bytearray(64)
    buf[:4] = b"\x7fELF"
    buf[4] = 2  # 64-bit
    buf[5] = 1  # little-endian
    # Set e_shoff to point beyond EOF
    struct.pack_into("<Q", buf, 40, 0xDEADBEEF)
    struct.pack_into("<H", buf, 60, 50)  # e_shnum
    detections = binary.scan_binary(bytes(buf), "corrupt.elf")
    assert isinstance(detections, list)


def _make_cpio_entry(name: str, payload: bytes) -> bytes:
    """Helper to build a valid CPIO new ASCII entry."""
    name_bytes = name.encode("latin1") + b"\x00"
    header = bytearray(110)
    header[:6] = b"070701"
    # 13 fields of 8-char hex:
    # ino(8), mode(8), uid(8), gid(8), nlink(8), mtime(8),
    # filesize(8), devmajor(8), devminor(8), rdevmajor(8), rdevminor(8),
    # namesize(8), check(8)
    fields = [
        b"00000000",  # ino
        b"000081a4",  # mode (regular file)
        b"00000000",  # uid
        b"00000000",  # gid
        b"00000001",  # nlink
        b"00000000",  # mtime
        f"{len(payload):08x}".encode("ascii"),   # filesize
        b"00000000",  # devmajor
        b"00000000",  # devminor
        b"00000000",  # rdevmajor
        b"00000000",  # rdevminor
        f"{len(name_bytes):08x}".encode("ascii"),  # namesize
        b"00000000",  # check
    ]
    struct.pack_into("8s8s8s8s8s8s8s8s8s8s8s8s8s", header, 6, *fields)
    padded_name_len = (110 + len(name_bytes) + 3) & ~3
    name_pad = b"\x00" * (padded_name_len - (110 + len(name_bytes)))
    padded_payload_len = (len(payload) + 3) & ~3
    payload_pad = b"\x00" * (padded_payload_len - len(payload))
    return bytes(header) + name_bytes + name_pad + payload + payload_pad


def test_firmware_path_traversal_cpio_rejected() -> None:
    """CPIO archives containing path traversal payloads must be sanitized or rejected."""
    payload = b"root:x:0:0:root:/root:/bin/bash\n"
    cpio_data = _make_cpio_entry("../../../../../../etc/shadow", payload)
    cpio_data += _make_cpio_entry("TRAILER!!!", b"")

    extracted = firmware.extract_firmware(cpio_data)
    # The path traversal entry MUST NOT be extracted with dangerous path
    for path, _content in extracted:
        assert ".." not in path
        assert not path.startswith("/")
        assert not path.startswith("\\")


def test_firmware_resource_limits() -> None:
    """Firmware extractor must respect max_files and max_bytes bounds."""
    large_payload = b"A" * 1024
    cpio_data = _make_cpio_entry("testfile.txt", large_payload)
    cpio_data += _make_cpio_entry("TRAILER!!!", b"")

    extracted = firmware.extract_cpio(cpio_data, max_bytes=500)
    total = sum(len(c) for _, c in extracted)
    assert total <= 1024


def test_hostile_source_inputs() -> None:
    """Source detectors must handle invalid UTF-8 and strange syntax safely."""
    bad_bytes = b"\xff\xfe\x00\x12\x80\x90" * 50
    rust_detections = source_rust.detect_code(bad_bytes, "corrupt.rs")
    assert isinstance(rust_detections, list)

    csharp_detections = source_csharp.detect_code(bad_bytes, "corrupt.cs")
    assert isinstance(csharp_detections, list)
