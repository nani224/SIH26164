"""Rule-independent feature extractors for the Crypto Mass Conservation (CMC) engine.

Adversarially independent from the rule engine:
- tables.py: Bijection over 0..255 and constant tables with high Hamming distance
- entropy.py: Sustained high-entropy regions
- arx.py: ARX opcode density in binaries and rotate+xor AST subtrees in source
- bigint.py: Modular-exponentiation loop shapes
- framing.py: Structural PEM, DER ASN.1, and Base64 blobs
- literals.py: Large numeric arrays, key-length literals, high-entropy string constants
"""

from __future__ import annotations

import hashlib

from engine.extract.arx import extract_arx
from engine.extract.bigint import extract_bigint
from engine.extract.entropy import extract_entropy
from engine.extract.framing import extract_framing
from engine.extract.literals import extract_literals
from engine.extract.tables import extract_tables
from engine.models import Span

__all__ = [
    "extract_all",
    "extract_arx",
    "extract_bigint",
    "extract_entropy",
    "extract_framing",
    "extract_literals",
    "extract_tables",
]


def extract_all(
    source: bytes, path: str = "<source>", artifact_hash: str | None = None
) -> list[Span]:
    """Run all rule-independent extractors on an artifact and return all suspicion spans."""
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    all_spans: list[Span] = []
    all_spans.extend(extract_tables(source, path, artifact_hash))
    all_spans.extend(extract_entropy(source, path, artifact_hash))
    all_spans.extend(extract_arx(source, path, artifact_hash))
    all_spans.extend(extract_bigint(source, path, artifact_hash))
    all_spans.extend(extract_framing(source, path, artifact_hash))
    all_spans.extend(extract_literals(source, path, artifact_hash))

    # Sort spans deterministically by start offset, then end offset, then producing_rule
    all_spans.sort(key=lambda s: (s.start, s.end, s.producing_rule))
    return all_spans
