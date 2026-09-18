"""Maps a Detection's family to a PQC (or hardening) recommendation.

Deterministic lookup, mirroring the shape used by Phase 0's
backend/api/stub_data.py hand-built examples, generalized into a table so
the engine can produce the same shape for any detection. Cost deltas are
illustrative (byte-size deltas between classical and PQC parameter sizes
from backend/api/stub_data.py's PQC_CATALOG) -- not re-measured against a
real liboqs build (that's Phase 8).
"""

from __future__ import annotations

from api.models import Family, Recommendation, RiskCost
from engine.models import Detection
from engine.pqc import NIST_PQC_CATALOG, compute_cost_delta

_CLASSICAL_KEY_ESTABLISHMENT = {Family.DH, Family.ECDH, Family.X25519}
_CLASSICAL_SIGNATURE = {Family.DSA, Family.ECDSA, Family.ED25519}
_WEAK_SYMMETRIC = {Family.THREE_DES, Family.DES, Family.RC4, Family.BLOWFISH}
_WEAK_HASH = {Family.MD5, Family.SHA_1}
_SIGNING_FUNCTIONS = ("sign", "verify")

_PQC_BY_NAME = {spec.name: spec for spec in NIST_PQC_CATALOG}


def recommend(detection: Detection) -> Recommendation | None:
    family = detection.family
    if family is None:
        return None

    is_rsa_signature = family == Family.RSA and detection.function in _SIGNING_FUNCTIONS
    key_size = detection.key_size or 2048

    if family in _CLASSICAL_KEY_ESTABLISHMENT or (family == Family.RSA and not is_rsa_signature):
        target_name = "ML-KEM-1024" if key_size >= 3072 else "ML-KEM-768"
        target_spec = _PQC_BY_NAME[target_name]
        classical_pk = key_size // 8 if family == Family.RSA else (32 if family == Family.X25519 else 64)
        classical_wire = classical_pk
        return Recommendation(
            action=f"Migrate to {target_name} for key establishment (hybrid with X25519 during transition)",
            target=target_name,
            cost=compute_cost_delta(target_spec, classical_pk, classical_wire, classical_op_ms=0.01),
        )

    if family in _CLASSICAL_SIGNATURE or is_rsa_signature:
        target_name = "ML-DSA-87" if key_size >= 3072 else "ML-DSA-65"
        target_spec = _PQC_BY_NAME[target_name]
        classical_pk = key_size // 8 if family == Family.RSA else 64
        classical_wire = classical_pk
        return Recommendation(
            action=f"Migrate to {target_name} for digital signatures",
            target=target_name,
            cost=compute_cost_delta(target_spec, classical_pk, classical_wire, classical_op_ms=0.02),
        )

    if family in _WEAK_SYMMETRIC:
        return Recommendation(
            action=f"Replace {family.value} with AES-256-GCM or ChaCha20-Poly1305",
            target="AES-256-GCM",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=-0.01),
        )

    if family in _WEAK_HASH:
        return Recommendation(
            action=f"Replace {family.value} with SHA-256 (or a fast non-crypto hash if this "
            "is a non-security checksum)",
            target="SHA-2-256",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=0.0),
        )

    if family == Family.HMAC and detection.underlying_hash_family in _WEAK_HASH:
        return Recommendation(
            action="Move to HMAC-SHA-256",
            target="HMAC-SHA-2-256",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=0.0),
        )

    return None
