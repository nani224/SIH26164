"""Rule-independent Shannon entropy extractor.

Computes Shannon entropy profiles and flags sustained high-entropy regions
inside otherwise low-entropy artifacts (e.g. encrypted payloads, random keys,
or compressed crypto structures embedded in code or binaries).

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter

from engine.models import Span


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


def extract_entropy(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    n = len(source)
    if n < 64:
        return []

    overall_entropy = shannon_entropy(source)
    # Thresholds:
    # If file is text / source code, baseline entropy is low (~4.0 - 5.5). A sustained region with H >= 6.8 is suspicious.
    # If binary, baseline is ~5.5 - 6.5. A sustained region with H >= 7.4 is suspicious.
    is_source = path.endswith((".py", ".go", ".java", ".c", ".h", ".cpp", ".js", ".ts", ".txt", ".json"))
    threshold = 6.8 if is_source else 7.4

    window_size = 128 if n >= 256 else 64
    step = 32

    high_windows: list[tuple[int, int]] = []
    for i in range(0, n - window_size + 1, step):
        w = source[i : i + window_size]
        h = shannon_entropy(w)
        if h >= threshold:
            high_windows.append((i, i + window_size))

    if not high_windows:
        return []

    # Merge contiguous or overlapping high-entropy windows
    merged: list[tuple[int, int]] = []
    cur_start, cur_end = high_windows[0]
    for w_start, w_end in high_windows[1:]:
        if w_start <= cur_end:
            cur_end = max(cur_end, w_end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = w_start, w_end
    merged.append((cur_start, cur_end))

    spans: list[Span] = []
    for start, end in merged:
        # Require sustained length (>= 64 bytes)
        if end - start >= 64:
            spans.append(
                Span(
                    artifact_hash=artifact_hash,
                    kind="byte",
                    start=start,
                    end=end,
                    producing_rule="extract.entropy.sustained_high",
                    signal_type="entropy.high_density",
                    magnitude=float(end - start),
                )
            )

    return spans
