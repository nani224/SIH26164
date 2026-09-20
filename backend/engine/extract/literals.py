"""Rule-independent literal extractor.

Detects:
1. Large numeric literal arrays in source code.
2. Key-length-shaped literals (256, 512, 1024, 2048, 3072, 4096).
3. High-entropy string constants in source code.

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from engine.models import Span

_KEY_LENGTHS = {256, 512, 1024, 2048, 3072, 4096, 8192}

# Key-length shaped patterns in code: key_size=2048, bits = 1024, or standalone key-size constants
_KEY_LENGTH_RE = re.compile(
    r"\b(?:key_?size|bits|key_?len|modulus_?size)\s*[:=]\s*(256|512|1024|2048|3072|4096|8192)\b|"
    r"\b(?:generate_key|make_key|new_key|genkey)\s*\([^)]*?\b(256|512|1024|2048|3072|4096|8192)\b",
    re.IGNORECASE,
)

# Numeric arrays: [0x12, 0x34, ...] or { 0x12, 0x34, ... }
_ARRAY_LITERAL_RE = re.compile(
    r"\[\s*(?:(?:0x[0-9a-fA-F]+|\d+)\s*,\s*){7,}(?:0x[0-9a-fA-F]+|\d+)\s*\]|"
    r"\{\s*(?:(?:0x[0-9a-fA-F]+|\d+)\s*,\s*){7,}(?:0x[0-9a-fA-F]+|\d+)\s*\}",
)

# Quoted string literals
_STRING_LITERAL_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'')


def _str_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def extract_literals(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    spans: list[Span] = []
    text = source.decode("latin1", errors="ignore")

    # 1. Key-length shaped literals
    for match in _KEY_LENGTH_RE.finditer(text):
        spans.append(
            Span(
                artifact_hash=artifact_hash,
                kind="ast",
                start=match.start(),
                end=match.end(),
                producing_rule="extract.literals.key_length",
                signal_type="literals.key_length",
                magnitude=float(match.end() - match.start()),
            )
        )

    # 2. Large numeric literal arrays
    for match in _ARRAY_LITERAL_RE.finditer(text):
        m_start, m_end = match.start(), match.end()
        if not any(s.start <= m_start and m_end <= s.end for s in spans):
            spans.append(
                Span(
                    artifact_hash=artifact_hash,
                    kind="ast",
                    start=m_start,
                    end=m_end,
                    producing_rule="extract.literals.numeric_array",
                    signal_type="literals.numeric_array",
                    magnitude=float(m_end - m_start),
                )
            )

    # 3. High-entropy string constants (length >= 32, entropy >= 4.5)
    for match in _STRING_LITERAL_RE.finditer(text):
        content = match.group(1) if match.group(1) is not None else match.group(2)
        if content and len(content) >= 32:
            h = _str_entropy(content)
            if h >= 4.5:
                m_start, m_end = match.start(), match.end()
                if not any(s.start <= m_start and m_end <= s.end for s in spans):
                    spans.append(
                        Span(
                            artifact_hash=artifact_hash,
                            kind="ast",
                            start=m_start,
                            end=m_end,
                            producing_rule="extract.literals.high_entropy_string",
                            signal_type="literals.high_entropy_string",
                            magnitude=float(m_end - m_start),
                        )
                    )

    return spans
