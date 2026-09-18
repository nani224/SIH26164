"""Authoritative NIST Post-Quantum Cryptography (PQC) catalog and agility metrics.

Phase 8: Provides formal parameter sets and cost delta models for NIST standardized
PQC algorithms (FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA) benchmarked
against classical baselines (RSA, ECDSA, ECDH, X25519).
"""

from __future__ import annotations

from dataclasses import dataclass

from api.models import Family, PqcCatalogEntry, RiskCost


@dataclass(frozen=True)
class PqcSpec:
    family: Family
    name: str
    standard: str
    parameter_set: str
    security_category: int
    public_key_bytes: int
    wire_bytes: int  # ciphertext for KEM, signature for DSA
    op_ms: float
    notes: str

    def to_catalog_entry(self) -> PqcCatalogEntry:
        return PqcCatalogEntry(
            family=self.family,
            displayName=self.name,
            standard=self.standard,
            parameterSet=self.parameter_set,
            securityCategory=self.security_category,
            publicKeyBytes=self.public_key_bytes,
            ciphertextOrSignatureBytes=self.wire_bytes,
            notes=self.notes,
        )


# NIST Standardized PQC parameter catalog
NIST_PQC_CATALOG: list[PqcSpec] = [
    PqcSpec(
        Family.ML_KEM, "ML-KEM-512", "FIPS 203", "ML-KEM-512", 1,
        800, 768, 0.03,
        "NIST Level 1 (AES-128 equivalent). Suitable for constrained devices.",
    ),
    PqcSpec(
        Family.ML_KEM, "ML-KEM-768", "FIPS 203", "ML-KEM-768", 3,
        1184, 1088, 0.05,
        "Recommended default KEM parameter set (NIST Level 3, roughly AES-192 equivalent).",
    ),
    PqcSpec(
        Family.ML_KEM, "ML-KEM-1024", "FIPS 203", "ML-KEM-1024", 5,
        1568, 1568, 0.08,
        "Highest security category KEM parameter set (NIST Level 5, AES-256 equivalent).",
    ),
    PqcSpec(
        Family.ML_DSA, "ML-DSA-44", "FIPS 204", "ML-DSA-44", 2,
        1312, 2420, 0.06,
        "NIST Level 2 signature parameter set.",
    ),
    PqcSpec(
        Family.ML_DSA, "ML-DSA-65", "FIPS 204", "ML-DSA-65", 3,
        1952, 3309, 0.08,
        "Recommended default signature parameter set (NIST Level 3).",
    ),
    PqcSpec(
        Family.ML_DSA, "ML-DSA-87", "FIPS 204", "ML-DSA-87", 5,
        2592, 4627, 0.12,
        "Highest security category signature parameter set (NIST Level 5).",
    ),
    PqcSpec(
        Family.SLH_DSA, "SLH-DSA-SHA2-128s", "FIPS 205", "SLH-DSA-SHA2-128s", 1,
        32, 7856, 1.20,
        "Stateless hash-based signature; compact keys, small ('s') signature variant.",
    ),
    PqcSpec(
        Family.SLH_DSA, "SLH-DSA-SHA2-128f", "FIPS 205", "SLH-DSA-SHA2-128f", 1,
        32, 17088, 0.15,
        "Stateless hash-based signature; fast ('f') signing variant, larger signature.",
    ),
    PqcSpec(
        Family.SLH_DSA, "SLH-DSA-SHA2-192f", "FIPS 205", "SLH-DSA-SHA2-192f", 3,
        48, 35664, 0.35,
        "Stateless hash-based signature; Level 3 fast variant.",
    ),
]


def compute_cost_delta(
    pqc_target: PqcSpec,
    classical_pk_bytes: int,
    classical_wire_bytes: int,
    classical_op_ms: float = 0.02,
) -> RiskCost:
    """Computes exact delta in public key size, wire bytes, and operation time."""
    return RiskCost(
        pkBytesDelta=pqc_target.public_key_bytes - classical_pk_bytes,
        wireBytesDelta=pqc_target.wire_bytes - classical_wire_bytes,
        opMsDelta=round(pqc_target.op_ms - classical_op_ms, 4),
    )
