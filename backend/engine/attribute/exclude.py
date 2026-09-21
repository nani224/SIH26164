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



# 16-element half-byte (nibble) CRC-32 table values
_CRC32_NIBBLE_INTS: frozenset[int] = frozenset([
    0, 0x1DB71064, 0x3B6E20C8, 0x26D930AC, 0x76DC4190, 0x6B6B51F4, 0x4DB26158, 0x5005713C,
    0x9B64C2B0, 0x86D3D2D4, 0xA00AE278, 0xBDBDF21C, 0xEDB88320, 0xF00F9344, 0xD6D6A3E8, 0xCB61B38C,
])

# 256-element full IEEE 802.3 CRC-32 table values
_CRC32_FULL_INTS: frozenset[int] = frozenset(
    struct.unpack("<256I", _CRC32_TABLE_BYTES)
)


def _parse_ints_from_array(slice_bytes: bytes) -> list[int]:
    """Parse integer and hex literals from a numeric array code slice."""
    import contextlib
    import re
    text = slice_bytes.decode("latin1", errors="ignore")
    nums = re.findall(r"0x[0-9a-fA-F]+|\d+", text)
    res: list[int] = []
    for n in nums:
        with contextlib.suppress(ValueError):
            res.append(int(n, 16) if n.startswith(("0x", "0X")) else int(n, 10))
    return res


def is_crc_numeric_array(slice_bytes: bytes) -> tuple[bool, str]:
    """Falsifiable: integer set matches standard 256-entry or 16-entry CRC-32 lookup table."""
    ints = _parse_ints_from_array(slice_bytes)
    if not ints:
        return False, ""
    int_set = frozenset(ints)
    if int_set == _CRC32_FULL_INTS:
        return True, "Numeric array matches IEEE 802.3 CRC-32 polynomial (0xEDB88320) 256-word table"
    if int_set == _CRC32_NIBBLE_INTS:
        return True, "Numeric array matches IEEE 802.3 CRC-32 half-byte (nibble) 16-word table"
    return False, ""


def is_ascii_text_asn1(slice_bytes: bytes) -> tuple[bool, str]:
    """Falsifiable: byte slice is >= 95% printable ASCII text/whitespace where byte 0x30 is ASCII '0'."""
    if not slice_bytes:
        return False, ""
    printable_count = sum(1 for b in slice_bytes if (32 <= b <= 126) or b in b"\r\n\t")
    if (printable_count / len(slice_bytes)) >= 0.95:
        return True, "Byte slice is printable ASCII text/code where 0x30 is ASCII '0', not ASN.1 DER sequence"
    return False, ""


def is_source_quote_bleed(slice_bytes: bytes) -> tuple[bool, str]:
    """Falsifiable: single-quoted or multiline string span contains comment delimiters or preprocessor directives."""
    if b"/*" in slice_bytes or b"*/" in slice_bytes:
        return True, "String span crosses C block comment delimiters (/* or */)"
    if b"#define" in slice_bytes or b"#include" in slice_bytes or b"#endif" in slice_bytes:
        return True, "String span crosses C preprocessor directives (#define, #include, #endif)"
    if slice_bytes.startswith(b"'") and b"\n" in slice_bytes:
        return True, "Single-quoted character literal span crosses newline boundaries in source code"
    return False, ""


def is_benign_arx(slice_bytes: bytes) -> tuple[bool, str]:
    """Falsifiable: ARX expression is CRC accumulator logic or Big-O asymptotic notation."""
    low = slice_bytes.lower()
    if b"crc" in low:
        return True, "ARX expression operates on CRC polynomial table or accumulator"
    if b"o(n^" in low or b"o(1)" in low or b"o(n)" in low:
        return True, "Expression is asymptotic Big-O complexity notation in code or comments"
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

        # 4. CRC-32 numeric arrays in source code
        if span.signal_type == "literals.numeric_array":
            is_crc, crc_reason = is_crc_numeric_array(slice_bytes)
            if is_crc:
                rec = ExclusionRecord(
                    span=span,
                    predicate_id="benign_crc_table",
                    falsifiable_reason=crc_reason,
                    content_hash=slice_hash,
                )
                excluded_spans.append(span)
                records.append(rec)
                continue

        # 5. Framing ASN.1 DER false-positives in ASCII source text
        if span.signal_type == "framing.asn1_der":
            is_ascii, ascii_reason = is_ascii_text_asn1(slice_bytes)
            if is_ascii:
                rec = ExclusionRecord(
                    span=span,
                    predicate_id="ascii_text_not_der",
                    falsifiable_reason=ascii_reason,
                    content_hash=slice_hash,
                )
                excluded_spans.append(span)
                records.append(rec)
                continue

        # 6. High-entropy string literals crossing source code comments or statements
        if span.signal_type == "literals.high_entropy_string":
            is_bleed, bleed_reason = is_source_quote_bleed(slice_bytes)
            if is_bleed:
                rec = ExclusionRecord(
                    span=span,
                    predicate_id="source_quote_bleed",
                    falsifiable_reason=bleed_reason,
                    content_hash=slice_hash,
                )
                excluded_spans.append(span)
                records.append(rec)
                continue

        # 7. Non-crypto ARX (CRC checksums or Big-O notation)
        if span.signal_type == "arx.source_composite":
            is_ben_arx, arx_reason = is_benign_arx(slice_bytes)
            if is_ben_arx:
                rec = ExclusionRecord(
                    span=span,
                    predicate_id="benign_arx",
                    falsifiable_reason=arx_reason,
                    content_hash=slice_hash,
                )
                excluded_spans.append(span)
                records.append(rec)
                continue

        # If no falsifiable exclusion predicate matches, it remains RESIDUE
        residue_spans.append(span)

    return excluded_spans, residue_spans, records
