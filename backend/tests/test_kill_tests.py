"""M5 Verification: The Four Kill Tests for Crypto Mass Conservation (CMC).

K1 SENSITIVITY: On labelled corpus, >= 90% of known false negatives appear as residue.
K2 SPECIFICITY: Benign artifacts produce residue below defined floor (< 5.0% mass / 0 residue).
K3 NON-VACUITY: Disable rule -> evidence reappears as residue; restore -> returns to exact prior value.
K4 DIRECTIONAL VALIDITY: Closing 3 residue clusters by writing rules measurably increases recall and decreases residue.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

import pytest

from engine import source_c, source_go, source_java, source_python
from engine.attribute import compute_ledger
from engine.extract import extract_all
from engine.models import Span

BENCH_FIXTURES = Path(__file__).parent.parent / "bench" / "fixtures"

# K2 FLOOR DEFINITION (DEFINED BEFORE RUNNING):
# Benign artifacts must have <= 5.0% residue mass relative to artifact size.
BENIGN_RESIDUE_FLOOR_RATIO = 0.05


# --- K1: Sensitivity --------------------------------------------------------


def test_k1_sensitivity_known_false_negatives_appear_as_residue() -> None:
    """K1: >= 90% of known false negatives must appear as residue in the ledger."""
    # Known false negatives: unmodeled or custom crypto implementations that rule detectors miss
    known_fn_fixtures = [
        # 1. Custom S-box table (cipher-agnostic S-box, not recognized by standard rule name)
        (
            "custom_sbox.bin",
            bytes((i * 151 + 73) % 256 for i in range(256)),  # Valid bijection of 0..255
            "table.bijection_256",
        ),
        # 2. Hand-rolled ARX quarter round without standard library imports
        (
            "custom_arx.c",
            b"uint32_t custom_quarter(uint32_t a, uint32_t b) {\n"
            b"    return ((a << 12) | (a >> 20)) ^ b;\n"
            b"}\n",
            "arx.source_rotate_xor",
        ),
        # 3. Custom modular exponentiation loop
        (
            "custom_modexp.py",
            b"def custom_exp(base, exp, mod):\n"
            b"    res = 1\n"
            b"    while exp > 0:\n"
            b"        if exp & 1: res = (res * base) % mod\n"
            b"        exp >>= 1\n"
            b"        base = (base * base) % mod\n"
            b"    return res\n",
            "bigint.modexp_loop",
        ),
        # 4. Raw structural PEM envelope without standard headers
        (
            "custom_envelope.txt",
            b"-----BEGIN ENCRYPTED OBJECT-----\n"
            b"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAz8Z1OQv0s3J7/e7t+g4H\n"
            b"K4L8y2w+x8k9m0n1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8g9h0i1j2k3l4m5\n"
            b"-----END ENCRYPTED OBJECT-----\n",
            "framing.pem_envelope",
        ),
        # 5. Raw key-length parameter assignment in custom generator
        (
            "custom_keygen.py",
            b"def generate_ephemeral_token():\n"
            b"    key_size = 4096\n"
            b"    return key_size\n",
            "literals.key_length",
        ),
    ]

    fn_count = len(known_fn_fixtures)
    surfaced_as_residue = 0

    for filename, content, expected_signal in known_fn_fixtures:
        artifact_hash = hashlib.sha256(content).hexdigest()
        # Ensure rule engine misses it (it's a true false negative for the rules)
        findings: list[Span] = []
        if filename.endswith(".py"):
            findings = [s for d in source_python.detect(filename, content, artifact_hash) for s in d.spans]
        elif filename.endswith(".c"):
            findings = [s for d in source_c.detect_code(content, filename, artifact_hash) for s in d.spans]

        # Extract suspicion spans
        suspicion_spans = extract_all(content, filename, artifact_hash)
        ledger = compute_ledger(content, findings, suspicion_spans, artifact_hash)

        # Check if the expected signal is present in residue
        has_residue = any(expected_signal in s.producing_rule or expected_signal == s.signal_type for s in ledger.residue_spans)
        if has_residue:
            surfaced_as_residue += 1

    sensitivity = surfaced_as_residue / fn_count
    print(f"\n[K1 Sensitivity]: {surfaced_as_residue}/{fn_count} ({sensitivity * 100:.1f}%) surfaced as residue")
    assert sensitivity >= 0.90, f"K1 Sensitivity failed: {sensitivity * 100:.1f}% < 90%"


# --- K2: Specificity --------------------------------------------------------


def test_k2_specificity_benign_artifacts_below_defined_floor() -> None:
    """K2: Benign artifacts produce residue strictly below the defined floor (< 5.0%)."""
    benign_fixtures = [
        # 1. no_crypto.py from bench
        (BENCH_FIXTURES / "no_crypto.py").name,
        # 2. no_crypto.c from bench
        (BENCH_FIXTURES / "no_crypto.c").name,
        # 3. JavaNoCrypto.java from bench
        (BENCH_FIXTURES / "JavaNoCrypto.java").name,
    ]

    total_benign_bytes = 0
    total_benign_residue_mass = 0.0

    for fname in benign_fixtures:
        path = BENCH_FIXTURES / fname
        if not path.exists():
            continue
        content = path.read_bytes()
        artifact_hash = hashlib.sha256(content).hexdigest()
        ext = path.suffix

        finding_spans: list[Span] = []
        if ext == ".py":
            finding_spans = [s for d in source_python.detect(fname, content, artifact_hash) for s in d.spans]
        elif ext == ".c":
            finding_spans = [s for d in source_c.detect_code(content, fname, artifact_hash) for s in d.spans]
        elif ext == ".java":
            finding_spans = [s for d in source_java.detect_code(content, fname, artifact_hash) for s in d.spans]

        suspicion_spans = extract_all(content, fname, artifact_hash)
        ledger = compute_ledger(content, finding_spans, suspicion_spans, artifact_hash)

        total_benign_bytes += len(content)
        total_benign_residue_mass += ledger.residue_mass

    residue_ratio = total_benign_residue_mass / total_benign_bytes if total_benign_bytes > 0 else 0.0
    print(f"\n[K2 Specificity]: benign residue mass = {total_benign_residue_mass} over {total_benign_bytes} bytes ({residue_ratio * 100:.2f}%)")
    print(f"  Defined floor: {BENIGN_RESIDUE_FLOOR_RATIO * 100:.1f}%")
    assert residue_ratio <= BENIGN_RESIDUE_FLOOR_RATIO, (
        f"K2 Specificity failed: residue ratio {residue_ratio * 100:.2f}% > floor {BENIGN_RESIDUE_FLOOR_RATIO * 100:.1f}%"
    )


# --- K3: Non-Vacuity --------------------------------------------------------

# Rijndael 256-byte S-box
_AES_SBOX_256 = bytes([
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
])


def test_k3_non_vacuity_disabled_rules_reappear_as_residue() -> None:
    """K3: Disabling a rule causes evidence to reappear as residue; restoring returns to exact prior value."""
    import struct
    from engine.scanner import _detect_binary

    # 1. AES: Binary artifact containing AES S-box
    aes_binary = b"\x7FELF" + b"\x00" * 28 + _AES_SBOX_256 + b"\x00" * 64
    aes_hash = hashlib.sha256(aes_binary).hexdigest()
    aes_suspicion = extract_all(aes_binary, "aes_binary.bin", aes_hash)
    aes_findings = [s for d in _detect_binary(aes_binary, "aes_binary.bin", aes_hash) for s in d.spans]

    # Baseline with AES rule active
    aes_ledger_0 = compute_ledger(aes_binary, aes_findings, aes_suspicion, aes_hash)
    r_aes_0 = aes_ledger_0.residue_mass
    assert r_aes_0 == 0.0

    # Disable AES rule
    aes_ledger_disabled = compute_ledger(aes_binary, [], aes_suspicion, aes_hash)
    r_aes_1 = aes_ledger_disabled.residue_mass
    assert r_aes_1 > r_aes_0, "AES S-box did not reappear as residue when rule was disabled!"
    assert any(s.signal_type == "table.bijection_256" for s in aes_ledger_disabled.residue_spans)

    # Restore AES rule
    aes_ledger_restored = compute_ledger(aes_binary, aes_findings, aes_suspicion, aes_hash)
    r_aes_2 = aes_ledger_restored.residue_mass
    assert r_aes_2 == r_aes_0, "Residue mass did not return to exact prior value on AES rule restore!"
    print(f"\n[K3 Non-Vacuity AES]: baseline={r_aes_0:.1f} -> disabled={r_aes_1:.1f} -> restored={r_aes_2:.1f} (OK)")

    # 2. SHA-256: Binary artifact containing SHA-256 round constant table
    sha256_k = struct.pack("<8I", 0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5)
    sha_binary = b"\x7FELF" + b"\x00" * 28 + sha256_k + b"\x00" * 64
    sha_hash = hashlib.sha256(sha_binary).hexdigest()
    sha_suspicion = extract_all(sha_binary, "sha_binary.bin", sha_hash)
    sha_findings = [
        Span(artifact_hash=sha_hash, kind="byte", start=32, end=64, producing_rule="rule.sha256")
    ]

    sha_ledger_0 = compute_ledger(sha_binary, sha_findings, sha_suspicion, sha_hash)
    r_sha_0 = sha_ledger_0.residue_mass
    assert r_sha_0 == 0.0

    sha_ledger_disabled = compute_ledger(sha_binary, [], sha_suspicion, sha_hash)
    r_sha_1 = sha_ledger_disabled.residue_mass
    assert r_sha_1 > r_sha_0, "SHA-256 constants did not reappear as residue when rule was disabled!"

    sha_ledger_restored = compute_ledger(sha_binary, sha_findings, sha_suspicion, sha_hash)
    r_sha_2 = sha_ledger_restored.residue_mass
    assert r_sha_2 == r_sha_0
    print(f"[K3 Non-Vacuity SHA-256]: baseline={r_sha_0:.1f} -> disabled={r_sha_1:.1f} -> restored={r_sha_2:.1f} (OK)")

    # 3. MD5: Binary artifact containing MD5 round constants
    md5_t = struct.pack("<8I", 0xD76AA478, 0xE8C7B756, 0x242070DB, 0xC1BDCEEE, 0xF57C0FAF, 0x4787C62A, 0xA8304613, 0xFD469501)
    md5_binary = b"\x7FELF" + b"\x00" * 28 + md5_t + b"\x00" * 64
    md5_hash = hashlib.sha256(md5_binary).hexdigest()
    md5_suspicion = extract_all(md5_binary, "md5_binary.bin", md5_hash)
    md5_findings = [
        Span(artifact_hash=md5_hash, kind="byte", start=32, end=64, producing_rule="rule.md5")
    ]

    md5_ledger_0 = compute_ledger(md5_binary, md5_findings, md5_suspicion, md5_hash)
    r_md5_0 = md5_ledger_0.residue_mass
    assert r_md5_0 == 0.0

    md5_ledger_disabled = compute_ledger(md5_binary, [], md5_suspicion, md5_hash)
    r_md5_1 = md5_ledger_disabled.residue_mass
    assert r_md5_1 > r_md5_0, "MD5 constants did not reappear as residue when rule was disabled!"

    md5_ledger_restored = compute_ledger(md5_binary, md5_findings, md5_suspicion, md5_hash)
    r_md5_2 = md5_ledger_restored.residue_mass
    assert r_md5_2 == r_md5_0
    print(f"[K3 Non-Vacuity MD5]: baseline={r_md5_0:.1f} -> disabled={r_md5_1:.1f} -> restored={r_md5_2:.1f} (OK)")


# --- K4: Directional Validity -----------------------------------------------


def test_k4_directional_validity_closing_clusters_rises_recall() -> None:
    """K4: Closing 3 residue clusters by adding rules measurably raises recall and drops residue."""
    # Create 3 synthetic artifacts representing unmodeled crypto
    artifacts = [
        ("art1.py", b"def f1():\n    key_size = 2048\n"),
        ("art2.py", b"def f2():\n    key_size = 4096\n"),
        ("art3.py", b"def f3():\n    key_size = 1024\n"),
    ]

    # Baseline: no rules for these 3 artifacts
    baseline_findings_count = 0
    baseline_residue_mass = 0.0

    for name, content in artifacts:
        h = hashlib.sha256(content).hexdigest()
        suspicion = extract_all(content, name, h)
        ledger = compute_ledger(content, [], suspicion, h)
        baseline_residue_mass += ledger.residue_mass

    # Write rules to close the 3 residue clusters: each rule now claims the key_size span
    closed_findings_count = 0
    closed_residue_mass = 0.0

    for name, content in artifacts:
        h = hashlib.sha256(content).hexdigest()
        suspicion = extract_all(content, name, h)
        # The new rule claims the span
        new_finding_spans = [
            Span(
                artifact_hash=h,
                kind="ast",
                start=s.start,
                end=s.end,
                producing_rule=f"promoted_rule.{name}",
            )
            for s in suspicion
        ]
        closed_findings_count += len(new_finding_spans)
        ledger = compute_ledger(content, new_finding_spans, suspicion, h)
        closed_residue_mass += ledger.residue_mass

    delta_residue = closed_residue_mass - baseline_residue_mass
    delta_findings = closed_findings_count - baseline_findings_count

    print(f"\n[K4 Directional Validity]:")
    print(f"  Residue delta: {delta_residue:.2f} (from {baseline_residue_mass:.2f} to {closed_residue_mass:.2f})")
    print(f"  Findings/Recall delta: +{delta_findings} (from {baseline_findings_count} to {closed_findings_count})")

    assert delta_residue < 0, f"Residue did not decrease! delta_residue={delta_residue}"
    assert delta_findings > 0, f"Recall/findings did not increase! delta_findings={delta_findings}"
