"""M2 Verification: Rule-independent extractor tests.

Verifies:
1. Architectural independence: NO module in engine/extract/ imports rules or detectors.
2. Each extractor has tests on a positive fixture and a benign negative fixture.
3. Determinism: identical input -> identical spans over 3 runs.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from engine.extract import (
    extract_all,
    extract_arx,
    extract_bigint,
    extract_entropy,
    extract_framing,
    extract_literals,
    extract_tables,
)
from engine.models import Span

EXTRACT_DIR = Path(__file__).parent.parent / "engine" / "extract"


def test_extract_independence_from_rules() -> None:
    """Architectural independence test: extract/ must NEVER import from rules/ or detectors."""
    forbidden_modules = {
        "engine.scanner",
        "engine.source_python",
        "engine.source_go",
        "engine.source_java",
        "engine.source_c",
        "engine.rules",
        "rules",
    }

    for py_file in EXTRACT_DIR.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Architectural violation in {py_file.name}: imports {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for forbidden in forbidden_modules:
                    assert not module.startswith(forbidden), (
                        f"Architectural violation in {py_file.name}: imports from {module}"
                    )
                if module == "engine":
                    for alias in node.names:
                        assert alias.name != "rules", (
                            f"Architectural violation in {py_file.name}: imports rules from engine"
                        )


# --- 1. Tables Extractor ----------------------------------------------------


def test_tables_positive_and_negative() -> None:
    # Positive: random permutation of 0..255 (a bijection / S-box shape)
    perm = bytes(list(range(256))[::-1])
    positive_spans = extract_tables(b"preface..." + perm + b"...postface")
    assert len(positive_spans) >= 1
    assert positive_spans[0].signal_type == "table.bijection_256"
    assert positive_spans[0].start == 10
    assert positive_spans[0].end == 266

    # Negative: 256 bytes of repeating characters (not a bijection)
    benign_text = b"This is a benign text document with no cryptographic S-boxes or constant tables. " * 4
    assert len(extract_tables(benign_text)) == 0


# --- 2. Entropy Extractor ---------------------------------------------------


def test_entropy_positive_and_negative() -> None:
    # Positive: 128 bytes of uniformly distributed random bytes (high entropy H ~ 8.0)
    import secrets

    # Deterministic pseudo-random 128 bytes with all 256 symbols evenly distributed
    random_blob = bytes((i * 97 + 13) % 256 for i in range(256))
    pre = b"def normal_code_function():\n    x = 1\n    return x\n" * 10
    post = b"\n# end of file\n"
    artifact = pre + random_blob + post

    spans = extract_entropy(artifact, path="test.py")
    assert len(spans) >= 1
    assert any(s.signal_type == "entropy.high_density" for s in spans)

    # Negative: standard python code (low entropy)
    benign_code = b"""
def calculate_average(values):
    if not values:
        return 0.0
    total = sum(values)
    return total / len(values)
"""
    assert len(extract_entropy(benign_code, path="calc.py")) == 0


# --- 3. ARX Extractor -------------------------------------------------------


def test_arx_positive_and_negative() -> None:
    # Positive source: rotate + xor expression
    arx_source = b"""
uint32_t quarter_round(uint32_t a, uint32_t b) {
    return ((a << 16) | (a >> (32 - 16))) ^ b;
}
"""
    spans = extract_arx(arx_source, path="arx.c")
    assert len(spans) >= 1
    assert any("arx" in s.signal_type for s in spans)

    # Negative source: plain arithmetic
    benign_c = b"""
int add_numbers(int a, int b) {
    int c = a + b;
    return c * 2;
}
"""
    assert len(extract_arx(benign_c, path="math.c")) == 0


# --- 4. BigInt Extractor ----------------------------------------------------


def test_bigint_positive_and_negative() -> None:
    # Positive: modular exponentiation loop with shift and modulo
    modexp_source = b"""
def mod_pow(base, exp, mod):
    res = 1
    while exp > 0:
        if exp & 1:
            res = (res * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return res
"""
    spans = extract_bigint(modexp_source, path="modexp.py")
    assert len(spans) >= 1
    assert spans[0].signal_type == "bigint.modexp_loop"

    # Negative: standard loop
    benign_loop = b"""
def print_numbers(n):
    for i in range(n):
        print(f"Item: {i}")
"""
    assert len(extract_bigint(benign_loop, path="loop.py")) == 0


# --- 5. Framing Extractor ---------------------------------------------------


def test_framing_positive_and_negative() -> None:
    # Positive: Structural PEM blob (valid base64 inside header/footer)
    pem_data = (
        b"-----BEGIN ENVELOPE-----\n"
        b"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAz8Z1OQv0s3J7/e7t+g4H\n"
        b"K4L8y2w+x8k9m0n1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8g9h0i1j2k3l4m5\n"
        b"-----END ENVELOPE-----\n"
    )
    spans = extract_framing(pem_data, path="blob.txt")
    assert len(spans) >= 1
    assert spans[0].signal_type == "framing.pem_envelope"

    # Negative: plain text
    benign_text = b"Hello, this is a plain text note with no framing or certificates."
    assert len(extract_framing(benign_text, path="note.txt")) == 0


# --- 6. Literals Extractor --------------------------------------------------


def test_literals_positive_and_negative() -> None:
    # Positive: key length literal and large numeric array
    code = b"""
key_size = 2048
table = [
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
]
"""
    spans = extract_literals(code, path="keys.py")
    assert len(spans) >= 1
    signal_types = {s.signal_type for s in spans}
    assert "literals.key_length" in signal_types or "literals.numeric_array" in signal_types

    # Negative: simple assignment
    benign_code = b"""
width = 100
height = 200
name = "Alice"
"""
    assert len(extract_literals(benign_code, path="ui.py")) == 0


# --- 7. Determinism across 3 runs -------------------------------------------


def test_extract_determinism_three_runs() -> None:
    sample_data = (
        b"-----BEGIN DATA-----\n"
        b"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAz8Z1OQv0s3J7/e7t+g4H\n"
        b"-----END DATA-----\n"
        b"key_size = 4096\n"
        b"while exp > 0:\n"
        b"    res = (res * base) % mod\n"
        b"    exp >>= 1\n"
    )
    run1 = extract_all(sample_data, "sample.py")
    run2 = extract_all(sample_data, "sample.py")
    run3 = extract_all(sample_data, "sample.py")

    assert len(run1) > 0
    assert run1 == run2 == run3
    for s1, s2, s3 in zip(run1, run2, run3):
        assert s1.start == s2.start == s3.start
        assert s1.end == s2.end == s3.end
        assert s1.producing_rule == s2.producing_rule == s3.producing_rule
        assert s1.signal_type == s2.signal_type == s3.signal_type
        assert s1.magnitude == s2.magnitude == s3.magnitude
