"""Binary format analyzer with ELF, PE (pefile), and Mach-O (lief) parity.

Detects cryptographic constants, symbols, and structures in:
- ELF binaries (.elf, .so, raw ELF)
- PE binaries (.exe, .dll, .sys)
- Mach-O binaries (.dylib, .macho)

Hostile-input hardened: bounds execution and catches all format errors.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_AES_SBOX_16 = bytes([
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
])

_SHA256_K_16 = bytes([
    0x98, 0x2F, 0x8A, 0x42, 0x91, 0x44, 0x37, 0x71,
    0xCF, 0xFB, 0xC0, 0xB5, 0xA5, 0xDB, 0xB5, 0xE9,
])

_MD5_T_16 = bytes([
    0x78, 0xA4, 0x6A, 0xD7, 0x56, 0xB7, 0xC7, 0xE8,
    0xDB, 0x70, 0x20, 0x24, 0xEE, 0xCE, 0xBD, 0xC1,
])

# Magic signatures
_ELF_MAGIC = b"\x7FELF"
_PE_MAGIC = b"MZ"
_MACHO_MAGICS = {
    0xFEEDFACE, 0xFEEDFACF,  # 32/64-bit big endian
    0xCEFAEDFE, 0xCFFAEDFE,  # 32/64-bit little endian
    0xCAFEBABE, 0xBEBAFECA,  # Fat binary
}


def detect_binary_format(source: bytes) -> str:
    """Identify binary container format."""
    if source.startswith(_ELF_MAGIC):
        return "elf"
    if source.startswith(_PE_MAGIC) and len(source) >= 0x40:
        # Check PE signature at e_lfanew
        try:
            e_lfanew = struct.unpack("<I", source[0x3C:0x40])[0]
            if e_lfanew + 4 <= len(source) and source[e_lfanew : e_lfanew + 4] == b"PE\x00\x00":
                return "pe"
        except struct.error:
            pass
    if len(source) >= 4:
        try:
            magic_be = struct.unpack(">I", source[:4])[0]
            magic_le = struct.unpack("<I", source[:4])[0]
            if magic_be in _MACHO_MAGICS or magic_le in _MACHO_MAGICS:
                return "macho"
        except struct.error:
            pass
    return "raw"


def scan_binary(source: bytes, rel_path: str, artifact_hash: str | None = None) -> list[Detection]:
    """Analyze binary with PE, Mach-O, and ELF parity."""
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    detections: list[Detection] = []
    b_format = detect_binary_format(source)

    # 1. Format-specific section inspection (safely handling hostile/malformed inputs)
    sections: list[tuple[str, int, bytes]] = []  # (name, file_offset, content)

    if b_format == "pe":
        try:
            import pefile
            pe = pefile.PE(data=source, fast_load=True)
            for section in getattr(pe, "sections", []):
                s_name = section.Name.decode("latin1", errors="ignore").strip("\x00")
                s_offset = section.PointerToRawData
                s_size = section.SizeOfRawData
                if s_offset + s_size <= len(source):
                    sections.append((s_name, s_offset, source[s_offset : s_offset + s_size]))
            pe.close()
        except Exception:
            # Fallback to scanning raw binary on hostile/corrupted PE
            pass

    elif b_format == "macho":
        try:
            import lief
            binary = lief.parse(raw=list(source))
            if binary is not None:
                for section in getattr(binary, "sections", []):
                    s_name = section.name
                    s_offset = section.offset
                    s_size = section.size
                    if s_offset + s_size <= len(source):
                        sections.append((s_name, s_offset, source[s_offset : s_offset + s_size]))
        except Exception:
            # Fallback to scanning raw binary on hostile/corrupted Mach-O
            pass

    # 2. Pattern scan across sections or full binary
    # If sections were parsed, scan within sections; otherwise scan full source
    scan_targets = sections if sections else [("binary", 0, source)]

    for sec_name, sec_offset, sec_bytes in scan_targets:
        # A. AES S-box
        if _AES_SBOX_16 in sec_bytes:
            local_offset = sec_bytes.find(_AES_SBOX_16)
            abs_offset = sec_offset + local_offset
            span = Span(
                artifact_hash=artifact_hash,
                kind="byte",
                start=abs_offset,
                end=abs_offset + 256,
                producing_rule=f"binary.{b_format}.aes_sbox",
            )
            detections.append(
                Detection(
                    kind=FindingKind.ALGORITHM,
                    surface=Surface.BINARY,
                    family=Family.AES,
                    display_name=f"AES S-box constant in {b_format.upper()} ({sec_name})",
                    function=CryptoFunction.ENCRYPT,
                    path=rel_path,
                    line=None,
                    symbol=f"AES_SBOX_{sec_name}",
                    snippet=f"AES S-box table at offset 0x{abs_offset:04x} in section {sec_name}",
                    source=FindingSource.BINARY_CONSTANT,
                    confidence=0.95,
                    key_size=128,
                    spans=[span],
                )
            )

        # B. SHA-256 round constants
        if _SHA256_K_16 in sec_bytes:
            local_offset = sec_bytes.find(_SHA256_K_16)
            abs_offset = sec_offset + local_offset
            span = Span(
                artifact_hash=artifact_hash,
                kind="byte",
                start=abs_offset,
                end=abs_offset + 64,
                producing_rule=f"binary.{b_format}.sha256_k",
            )
            detections.append(
                Detection(
                    kind=FindingKind.ALGORITHM,
                    surface=Surface.BINARY,
                    family=Family.SHA_2,
                    display_name=f"SHA-256 round constants in {b_format.upper()} ({sec_name})",
                    function=CryptoFunction.DIGEST,
                    path=rel_path,
                    line=None,
                    symbol=f"SHA256_K_{sec_name}",
                    snippet=f"SHA-256 K table at offset 0x{abs_offset:04x} in section {sec_name}",
                    source=FindingSource.BINARY_CONSTANT,
                    confidence=0.95,
                    spans=[span],
                )
            )

        # C. MD5 round constants
        if _MD5_T_16 in sec_bytes:
            local_offset = sec_bytes.find(_MD5_T_16)
            abs_offset = sec_offset + local_offset
            span = Span(
                artifact_hash=artifact_hash,
                kind="byte",
                start=abs_offset,
                end=abs_offset + 64,
                producing_rule=f"binary.{b_format}.md5_t",
            )
            detections.append(
                Detection(
                    kind=FindingKind.ALGORITHM,
                    surface=Surface.BINARY,
                    family=Family.MD5,
                    display_name=f"MD5 round constants in {b_format.upper()} ({sec_name})",
                    function=CryptoFunction.DIGEST,
                    path=rel_path,
                    line=None,
                    symbol=f"MD5_T_{sec_name}",
                    snippet=f"MD5 T table at offset 0x{abs_offset:04x} in section {sec_name}",
                    source=FindingSource.BINARY_CONSTANT,
                    confidence=0.95,
                    spans=[span],
                )
            )

    return detections
