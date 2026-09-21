"""Rule-independent BigInt modular exponentiation extractor.

Detects modular-exponentiation loop shapes: multiply-reduce cycles over big-int
strides (conservative: prefers misses over noise).

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import hashlib
import re

from engine.models import Span

# Conservative loop shapes for modular exponentiation:
# Loop with bitwise exponent shift / divide + modular multiplication / reduce
_MODEXP_LOOP_RE = re.compile(
    r"(?:for|while)\s*\([^)]*\)\s*\{[^}]*(?:>>=\s*1|>>\s*1|/\s*2|%=\s*|%\s*\w+)[^}]*(?:\*\s*=|mul)[^}]*\}|"
    r"(?:while\s+[^\n:]+:\s*\n(?:\s+[^\n]+\n)*?(?:\s+[^\n]*(?:>>=\s*1|//=\s*2)[^\n]*\n)(?:\s+[^\n]+\n)*?(?:\s+[^\n]*(?:%\s*\w+|\*=\s*)[^\n]*\n))",
    re.MULTILINE,
)

_MONTGOMERY_RE = re.compile(
    r"(?:montgomery_(?:reduce|mul|exp)|mod(?:_)?exp|pow_mod|modpow)\s*\(",
    re.IGNORECASE,
)


def extract_bigint(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    spans: list[Span] = []
    text = source.decode("latin1", errors="ignore")

    for match in _MODEXP_LOOP_RE.finditer(text):
        m_start, m_end = match.start(), match.end()
        # Conservative check: ensure both a reduction/modulo and multiplication/shift are present
        block = text[m_start:m_end]
        has_shift = ">>" in block or "/=" in block or "//" in block
        has_mod = "%" in block or "mod" in block.lower()
        has_mul = "*" in block or "mul" in block.lower()
        if has_shift and has_mod and has_mul:
            spans.append(
                Span(
                    artifact_hash=artifact_hash,
                    kind="ast",
                    start=m_start,
                    end=m_end,
                    producing_rule="extract.bigint.modexp_loop",
                    signal_type="bigint.modexp_loop",
                    magnitude=float(m_end - m_start),
                )
            )

    for match in _MONTGOMERY_RE.finditer(text):
        m_start, m_end = match.start(), match.end()
        if not any(s.start <= m_start and m_end <= s.end for s in spans):
            spans.append(
                Span(
                    artifact_hash=artifact_hash,
                    kind="ast",
                    start=m_start,
                    end=m_end,
                    producing_rule="extract.bigint.montgomery_call",
                    signal_type="bigint.montgomery_call",
                    magnitude=float(m_end - m_start),
                )
            )

    return spans
