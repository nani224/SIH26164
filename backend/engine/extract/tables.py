"""Rule-independent table extractor.

Detects:
1. Any 256-byte window that is a bijection over 0..255 (S-box shape, cipher-agnostic).
2. Constant tables (u32 / u64) with high pairwise Hamming distance and low repetition.

Adversarially independent: imports NO rules or algorithm constants.
"""

from __future__ import annotations

import hashlib
import re
import struct

from engine.models import Span


def _popcount(x: int) -> int:
    return bin(x).count("1")


def _pairwise_hamming_distance(words: list[int]) -> float:
    if len(words) < 2:
        return 0.0
    total_dist = sum(_popcount(words[i] ^ words[i + 1]) for i in range(len(words) - 1))
    return total_dist / (len(words) - 1)


_HEX_OR_INT_LITERAL = re.compile(r"0x[0-9a-fA-F]+|\b\d+\b")


def extract_tables(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    spans: list[Span] = []
    n = len(source)

    # 1. 256-byte sliding window bijection over 0..255
    if n >= 256:
        # Check byte windows
        i = 0
        while i <= n - 256:
            window = source[i : i + 256]
            if len(set(window)) == 256:
                spans.append(
                    Span(
                        artifact_hash=artifact_hash,
                        kind="byte",
                        start=i,
                        end=i + 256,
                        producing_rule="extract.tables.bijection_256",
                        signal_type="table.bijection_256",
                        magnitude=256.0,
                    )
                )
                i += 256
            else:
                i += 1

    # 2. Binary u32 constant tables (>= 8 words, unique, mean Hamming dist >= 12)
    # Check aligned 4-byte sequences in binary chunks across all 4 byte alignments
    if n >= 32:
        for align in (0, 1, 2, 3):
            sub = source[align:]
            word_count = len(sub) // 4
            if word_count < 8:
                continue
            words_le = [struct.unpack("<I", sub[j * 4 : (j + 1) * 4])[0] for j in range(word_count)]

            # Scan for runs of >= 8 unique words with high entropy / high hamming distance
            k = 0
            while k <= len(words_le) - 8:
                candidate = words_le[k : k + 8]
                non_ascii_count = sum(1 for w in candidate if (w & 0x80808080) != 0)
                high_bit_count = sum(1 for w in candidate if (w & 0x80000000) != 0)
                if (
                    non_ascii_count >= 5
                    and high_bit_count >= 2
                    and len(set(candidate)) == 8
                    and all(w >= 0x100 for w in candidate)
                    and _pairwise_hamming_distance(candidate) >= 12.0
                ):
                    # Extend as far as possible
                    end_k = k + 8
                    while end_k < len(words_le):
                        w = words_le[end_k]
                        if w in set(words_le[k:end_k]) or w < 0x100:
                            break
                        extended = words_le[k : end_k + 1]
                        if _pairwise_hamming_distance(extended) < 11.0:
                            break
                        end_k += 1

                    start_byte = align + k * 4
                    end_byte = align + end_k * 4
                    # Don't overlap with already detected bijection or existing table
                    if not any(max(s.start, start_byte) < min(s.end, end_byte) for s in spans):
                        spans.append(
                            Span(
                                artifact_hash=artifact_hash,
                                kind="byte",
                                start=start_byte,
                                end=end_byte,
                                producing_rule="extract.tables.constant_words",
                                signal_type="table.constant_words",
                                magnitude=float(end_byte - start_byte),
                            )
                        )
                    k = end_k
                else:
                    k += 1

    # 3. Source-code table parsing: array of 256 numbers forming a permutation
    # For source files, look for bracketed sequences containing 256 unique byte values
    if path.endswith((".py", ".c", ".h", ".cpp", ".java", ".go")):
        decoded = source.decode("latin1", errors="ignore")
        for match in re.finditer(r"\[([^\]]{500,4000})\]|\{([^}]{500,4000})\}", decoded):
            bracket_text = match.group(0)
            numbers: list[int] = []
            for num_str in _HEX_OR_INT_LITERAL.findall(bracket_text):
                try:
                    val = int(num_str, 16) if num_str.startswith("0x") else int(num_str)
                    numbers.append(val)
                except ValueError:
                    continue
            if len(numbers) == 256 and len(set(numbers)) == 256 and min(numbers) == 0 and max(numbers) == 255:
                spans.append(
                    Span(
                        artifact_hash=artifact_hash,
                        kind="ast",
                        start=match.start(),
                        end=match.end(),
                        producing_rule="extract.tables.bijection_256",
                        signal_type="table.bijection_256",
                        magnitude=float(match.end() - match.start()),
                    )
                )

    return spans
