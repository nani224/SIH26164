"""Rule-independent ARX (Add-Rotate-XOR) extractor.

Detects:
1. Binaries: opcode-density windows dominated by ROL/ROR/XOR/SHL/ADD.
2. Source: AST subtrees / expressions composing rotate and XOR over fixed-width ints.

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import hashlib
import re

from engine.models import Span

# Typical ARX source patterns:
# (x << n) | (x >> (32 - n)) ^ y
# (a + b) ^ (rot...)
_ARX_ROTATE_RE = re.compile(
    r"(?:\(?\s*\w+\s*<<\s*\d+\s*\)?\s*\|\s*\(?\s*\w+\s*>>\s*\(?(?:32|64|\d+)\s*(?:-\s*\d+)?\)?\s*\)?)|"
    r"(?:(?:rotate_left|RotateLeft|rotateLeft|rotl|rotr)\s*\([^)]+\))",
    re.IGNORECASE,
)

_ARX_EXPR_RE = re.compile(
    r"(?:(?:\([^)]+\)|[\w()]+)\s*\^\s*(?:\([^)]+\)|[\w()]+))|"
    r"(?:[\w()]+\s*\^\s*[\w()]+\s*(?:\+|\^|<<|>>)\s*[\w()]+)",
    re.IGNORECASE,
)

# Common x86/x64 ARX opcode bytes
_X86_ARX_OPCODES = {
    0x31, 0x33, 0x35,  # xor
    0x01, 0x03, 0x05,  # add
    0xC1, 0xD1, 0xD3,  # shifts / rotates (rol/ror/shl/shr)
}


def extract_arx(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    spans: list[Span] = []
    is_source = path.endswith((".py", ".go", ".java", ".c", ".h", ".cpp", ".cc", ".rs"))

    if is_source:
        # Source text scanning for ARX expressions
        text = source.decode("latin1", errors="ignore")
        for match in _ARX_ROTATE_RE.finditer(text):
            # Check context around rotate for XOR / ADD
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            ctx = text[start:end]
            if "^" in ctx or "+" in ctx:
                spans.append(
                    Span(
                        artifact_hash=artifact_hash,
                        kind="ast",
                        start=match.start(),
                        end=match.end(),
                        producing_rule="extract.arx.source_rotate_xor",
                        signal_type="arx.source_rotate_xor",
                        magnitude=float(match.end() - match.start()),
                    )
                )

        for match in _ARX_EXPR_RE.finditer(text):
            # Avoid duplicate spans if already covered
            m_start, m_end = match.start(), match.end()
            if not any(s.start <= m_start and m_end <= s.end for s in spans):
                spans.append(
                    Span(
                        artifact_hash=artifact_hash,
                        kind="ast",
                        start=m_start,
                        end=m_end,
                        producing_rule="extract.arx.source_composite",
                        signal_type="arx.source_composite",
                        magnitude=float(m_end - m_start),
                    )
                )
    else:
        # Binary opcode density scanning
        n = len(source)
        window_size = 64
        step = 16
        if n >= window_size:
            high_arx_windows: list[tuple[int, int]] = []
            for i in range(0, n - window_size + 1, step):
                window = source[i : i + window_size]
                arx_count = sum(1 for b in window if b in _X86_ARX_OPCODES)
                # If >= 35% of bytes in window match ARX opcodes, flag it
                if arx_count / window_size >= 0.35:
                    high_arx_windows.append((i, i + window_size))

            if high_arx_windows:
                # Merge overlapping windows
                merged: list[tuple[int, int]] = []
                cur_start, cur_end = high_arx_windows[0]
                for w_start, w_end in high_arx_windows[1:]:
                    if w_start <= cur_end:
                        cur_end = max(cur_end, w_end)
                    else:
                        merged.append((cur_start, cur_end))
                        cur_start, cur_end = w_start, w_end
                merged.append((cur_start, cur_end))

                for start, end in merged:
                    spans.append(
                        Span(
                            artifact_hash=artifact_hash,
                            kind="byte",
                            start=start,
                            end=end,
                            producing_rule="extract.arx.binary_opcode_density",
                            signal_type="arx.binary_opcode_density",
                            magnitude=float(end - start),
                        )
                    )

    return spans
