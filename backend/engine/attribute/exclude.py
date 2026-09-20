"""Falsifiable exclusion calculus for crypto-suspicion spans.

A suspicion span is EXCLUDED only via falsifiable predicates, each recorded with its reason:
- Benign-table registry keyed by content hash (CRC tables, compression tables, font/codec tables, Unicode tables)
- Non-cryptographic identity byte maps (e.g. table[i] == i)
- Base64 blobs that decode to plain text or media headers (PNG, JPEG, GIF)
- Documented benign shapes with verifiable predicates.

A predicate that cannot be stated falsifiably is NOT an exclusion.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import struct
from dataclasses import dataclass
from typing import Callable

from engine.models import Span


@dataclass(frozen=True)
class ExclusionRecord:
    span: Span
    predicate_id: str
    falsifiable_reason: str
    content_hash: str


# Pre-generate standard benign tables and their SHA-256 hashes
def _generate_crc32_table() -> bytes:
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            if c & 1:
                c = 0xEDB88320 ^ (c >> 1)
            else:
                c >>= 1
        table.append(c)
    return struct.pack(f"<{len(table)}I", *table)


_CRC32_TABLE_BYTES = _generate_crc32_table()
_CRC32_TABLE_HASH = hashlib.sha256(_CRC32_TABLE_BYTES).hexdigest()

_BASE64_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_BASE64_ALPHABET_HASH = hashlib.sha256(_BASE64_ALPHABET).hexdigest()

_HEX_LOWER = b"0123456789abcdef"
_HEX_LOWER_HASH = hashlib.sha256(_HEX_LOWER).hexdigest()

_HEX_UPPER = b"0123456789ABCDEF"
_HEX_UPPER_HASH = hashlib.sha256(_HEX_UPPER).hexdigest()

# Known benign table hashes
BENIGN_TABLE_HASHES: dict[str, str] = {
    _CRC32_TABLE_HASH: "IEEE 802.3 CRC-32 polynomial (0xEDB88320) lookup table",
    _BASE64_ALPHABET_HASH: "Standard RFC 4648 Base64 character encoding alphabet",
    _HEX_LOWER_HASH: "Lowercase hexadecimal character lookup table",
    _HEX_UPPER_HASH: "Uppercase hexadecimal character lookup table",
}


BENIGN_TABLE_REGISTRY: dict[bytes, tuple[str, str]] = {
    _CRC32_TABLE_BYTES: (_CRC32_TABLE_HASH, "IEEE 802.3 CRC-32 polynomial (0xEDB88320) lookup table"),
    _BASE64_ALPHABET: (_BASE64_ALPHABET_HASH, "Standard RFC 4648 Base64 character encoding alphabet"),
    _HEX_LOWER: (_HEX_LOWER_HASH, "Lowercase hexadecimal character lookup table"),
    _HEX_UPPER: (_HEX_UPPER_HASH, "Uppercase hexadecimal character lookup table"),
}


def is_identity_byte_table(slice_bytes: bytes) -> bool:
    """Falsifiable: 256-byte slice where slice[i] == i for all i in 0..255 (ASCII identity map)."""
    return len(slice_bytes) == 256 and bytes(range(256)) == slice_bytes


def is_media_or_plain_text_base64(slice_bytes: bytes) -> tuple[bool, str]:
    """Falsifiable: base64 payload decodes to media magic bytes or readable UTF-8 text."""
    # Strip whitespace/envelope markers
    clean = b"".join(line.strip() for line in slice_bytes.splitlines() if not line.strip().startswith(b"-----"))
    if not clean or len(clean) % 4 != 0:
        return False, ""
    try:
        decoded = base64.b64decode(clean, validate=True)
    except (binascii.Error, ValueError):
        return False, ""

    if decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, "Decoded payload starts with PNG magic header (0x89504E470D0A1A0A)"
    if decoded.startswith(b"\xFF\xD8\xFF"):
        return True, "Decoded payload starts with JPEG magic header (0xFFD8FF)"
    if decoded.startswith(b"GIF87a") or decoded.startswith(b"GIF89a"):
        return True, "Decoded payload starts with GIF magic header"
    if decoded.startswith(b"%PDF-"):
        return True, "Decoded payload starts with PDF magic header (%PDF-)"

    # Check if purely printable UTF-8 text with no null bytes and >= 90% ASCII printable
    if b"\x00" not in decoded:
        try:
            text = decoded.decode("utf-8")
            printable_ratio = sum(1 for c in text if c.isprintable() or c in "\r\n\t") / len(text)
            if printable_ratio >= 0.95 and len(text) >= 32:
                return True, f"Decoded payload is valid UTF-8 plain text ({printable_ratio * 100:.1f}% printable)"
        except UnicodeDecodeError:
            pass

    return False, ""


def evaluate_exclusions(
    spans: list[Span],
    artifact_content: bytes,
) -> tuple[list[Span], list[Span], list[ExclusionRecord]]:
    """Partition unclaimed suspicion spans into EXCLUDED vs RESIDUE.

    Returns:
        excluded_spans: Spans matched by a falsifiable exclusion predicate.
        residue_spans: Spans that are neither attributed nor excluded.
        records: Audit records for each exclusion.
    """
    excluded_spans: list[Span] = []
    residue_spans: list[Span] = []
    records: list[ExclusionRecord] = []

    for span in spans:
        slice_bytes = artifact_content[span.start : span.end]
        slice_hash = hashlib.sha256(slice_bytes).hexdigest()

        # 1. Benign-table registry match by content hash or substring overlap
        matched_benign = False
        tbl_reason = ""
        tbl_hash = slice_hash

        if slice_hash in BENIGN_TABLE_HASHES:
            matched_benign = True
            tbl_reason = BENIGN_TABLE_HASHES[slice_hash]
        else:
            for b_bytes, (b_hash, b_desc) in BENIGN_TABLE_REGISTRY.items():
                if b_bytes in slice_bytes or slice_bytes in b_bytes:
                    matched_benign = True
                    tbl_reason = b_desc
                    tbl_hash = b_hash
                    break

        if matched_benign:
            rec = ExclusionRecord(
                span=span,
                predicate_id="benign_table_registry",
                falsifiable_reason=f"Content matches registered benign table: {tbl_reason}",
                content_hash=tbl_hash,
            )
            excluded_spans.append(span)
            records.append(rec)
            continue

        # 2. Identity byte mapping table check (table[i] == i)
        if span.signal_type == "table.bijection_256" and is_identity_byte_table(slice_bytes):
            rec = ExclusionRecord(
                span=span,
                predicate_id="identity_byte_mapping",
                falsifiable_reason="256-byte sequence is identity mapping bytes(range(256)), not a cryptographic S-box",
                content_hash=slice_hash,
            )
            excluded_spans.append(span)
            records.append(rec)
            continue

        # 3. Base64 / framing media or plain text check
        if span.signal_type in ("framing.base64_blob", "framing.pem_envelope"):
            is_media, media_reason = is_media_or_plain_text_base64(slice_bytes)
            if is_media:
                rec = ExclusionRecord(
                    span=span,
                    predicate_id="media_or_text_payload",
                    falsifiable_reason=media_reason,
                    content_hash=slice_hash,
                )
                excluded_spans.append(span)
                records.append(rec)
                continue

        # If no falsifiable exclusion predicate matches, it remains RESIDUE
        residue_spans.append(span)

    return excluded_spans, residue_spans, records
