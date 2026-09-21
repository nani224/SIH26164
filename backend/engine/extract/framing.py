"""Rule-independent framing extractor.

Detects PEM, DER, ASN.1, and base64-shaped structural blobs WITHOUT relying on
specific cryptographic keywords (e.g. "CERTIFICATE", "RSA PRIVATE KEY").

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re

from engine.models import Span

# PEM structural envelope: any header/footer delimiter with base64 payload inside
_STRUCTURAL_PEM_RE = re.compile(
    rb"-----[A-Z0-9 _-]+-----\s*[\r\n]+([A-Za-z0-9+/=\s]{40,})[\r\n]+-----[A-Z0-9 _-]+-----"
)

# Bare base64 multiline structural blob (lines of 64 or 76 chars, multiple of 4, valid base64)
_STRUCTURAL_BASE64_BLOCK_RE = re.compile(
    rb"(?:[A-Za-z0-9+/]{64}[\r\n]+){2,}[A-Za-z0-9+/]{4,64}={0,2}"
)


def _validate_der_sequence(data: bytes, offset: int) -> int | None:
    """Check if data at offset starts a valid ASN.1 DER SEQUENCE. Returns total length if valid."""
    n = len(data)
    if offset + 4 > n:
        return None
    if data[offset] != 0x30:  # SEQUENCE tag
        return None

    len_byte = data[offset + 1]
    if len_byte < 0x80:
        length = len_byte
        header_len = 2
    elif len_byte == 0x81:
        length = data[offset + 2]
        header_len = 3
    elif len_byte == 0x82:
        if offset + 4 > n:
            return None
        length = (data[offset + 2] << 8) | data[offset + 3]
        header_len = 4
    else:
        return None

    total_len = header_len + length
    if length < 32 or offset + total_len > n:
        return None

    # Structural check of inner elements: should start with a recognized ASN.1 tag
    inner_offset = offset + header_len
    first_tag = data[inner_offset]
    # Common ASN.1 tags: 0x02 (INTEGER), 0x03 (BIT STRING), 0x04 (OCTET STRING), 0x06 (OID), 0x30 (SEQUENCE), 0x31 (SET)
    if first_tag in {0x02, 0x03, 0x04, 0x06, 0x30, 0x31}:
        return total_len

    return None


def extract_framing(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    spans: list[Span] = []
    n = len(source)

    # 1. Structural PEM
    for match in _STRUCTURAL_PEM_RE.finditer(source):
        # Validate that the inner payload actually base64-decodes
        payload = re.sub(rb"\s+", b"", match.group(1))
        if len(payload) % 4 == 0:
            try:
                decoded = base64.b64decode(payload, validate=True)
                if len(decoded) >= 24:
                    spans.append(
                        Span(
                            artifact_hash=artifact_hash,
                            kind="byte",
                            start=match.start(),
                            end=match.end(),
                            producing_rule="extract.framing.pem_envelope",
                            signal_type="framing.pem_envelope",
                            magnitude=float(match.end() - match.start()),
                        )
                    )
            except (binascii.Error, ValueError):
                continue

    # 2. Structural Base64 multiline blocks (if not inside PEM)
    for match in _STRUCTURAL_BASE64_BLOCK_RE.finditer(source):
        m_start, m_end = match.start(), match.end()
        if not any(s.start <= m_start and m_end <= s.end for s in spans):
            payload = re.sub(rb"\s+", b"", match.group(0))
            if len(payload) % 4 == 0:
                try:
                    decoded = base64.b64decode(payload, validate=True)
                    if len(decoded) >= 48:
                        spans.append(
                            Span(
                                artifact_hash=artifact_hash,
                                kind="byte",
                                start=m_start,
                                end=m_end,
                                producing_rule="extract.framing.base64_blob",
                                signal_type="framing.base64_blob",
                                magnitude=float(m_end - m_start),
                            )
                        )
                except (binascii.Error, ValueError):
                    continue

    # 3. Structural ASN.1 DER Sequences in binary
    i = 0
    while i < n - 32:
        der_len = _validate_der_sequence(source, i)
        if der_len is not None:
            if not any(s.start <= i and i + der_len <= s.end for s in spans):
                spans.append(
                    Span(
                        artifact_hash=artifact_hash,
                        kind="byte",
                        start=i,
                        end=i + der_len,
                        producing_rule="extract.framing.asn1_der",
                        signal_type="framing.asn1_der",
                        magnitude=float(der_len),
                    )
                )
            i += der_len
        else:
            i += 1

    return spans
