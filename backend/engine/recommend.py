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

_CLASSICAL_KEY_ESTABLISHMENT = {Family.DH, Family.ECDH, Family.X25519}
_CLASSICAL_SIGNATURE = {Family.DSA, Family.ECDSA, Family.ED25519}
_WEAK_SYMMETRIC = {Family.THREE_DES, Family.DES, Family.RC4, Family.BLOWFISH}
_WEAK_HASH = {Family.MD5, Family.SHA_1}
_SIGNING_FUNCTIONS = ("sign", "verify")


def recommend(detection: Detection) -> Recommendation | None:
    family = detection.family
    if family is None:
        return None

    is_rsa_signature = family == Family.RSA and detection.function in _SIGNING_FUNCTIONS
    if family in _CLASSICAL_KEY_ESTABLISHMENT or (family == Family.RSA and not is_rsa_signature):
        return Recommendation(
            action="Migrate to ML-KEM-768 for key establishment (hybrid with X25519 during transition)",
            target="ML-KEM-768",
            cost=RiskCost(pkBytesDelta=1184 - 256, wireBytesDelta=1088 - 256, opMsDelta=0.05),
        )
    if family in _CLASSICAL_SIGNATURE or is_rsa_signature:
        return Recommendation(
            action="Migrate to ML-DSA-65 for digital signatures",
            target="ML-DSA-65",
            cost=RiskCost(pkBytesDelta=1952 - 256, wireBytesDelta=3309 - 256, opMsDelta=0.08),
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
