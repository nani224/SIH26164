# ADR 008: Phase 8 Standardized NIST PQC Catalog and Agility Metrics

Status: accepted
Date: 2026-09-18

## Context

SIH26164 requires clear cryptographic migration paths and recommendations for vulnerable classical algorithms towards Post-Quantum Cryptography (PQC).
In August 2024, NIST released the initial finalized Post-Quantum Cryptography standards:
- FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism (ML-KEM)
- FIPS 204: Module-Lattice-Based Digital Signature Algorithm (ML-DSA)
- FIPS 205: Stateless Hash-Based Digital Signature Algorithm (SLH-DSA)

Previously, ECDAT provided generic, hardcoded migration strings and heuristic agility cost multipliers without formal parameter sets or security category matching.

## Decision

1. **Authoritative NIST Specification Catalog (`backend/engine/pqc.py`)**:
   - Defined `PqcSpec` with formal parameter sets:
     - FIPS 203: ML-KEM-512 (Category 1), ML-KEM-768 (Category 3), ML-KEM-1024 (Category 5).
     - FIPS 204: ML-DSA-44 (Category 2), ML-DSA-65 (Category 3), ML-DSA-87 (Category 5).
     - FIPS 205: SLH-DSA-SHA2-128s, SLH-DSA-SHAKE-128s (Category 1).
   - Provided public key size, wire/ciphertext size, operational latency, and standard designations.

2. **Standard-Aligned Recommendations (`backend/engine/recommend.py`)**:
   - Mapped classical algorithms directly to standardized FIPS replacements based on function and security level:
     - Asymmetric encryption / key exchange (RSA, DH, ECDH, X25519) -> ML-KEM (ML-KEM-768 by default; ML-KEM-1024 for RSA >= 3072-bit or high security).
     - Digital signatures (RSA sign, ECDSA, Ed25519) -> ML-DSA (ML-DSA-65 by default; ML-DSA-87 for high security).
     - Symmetric ciphers (AES-128, 3DES, DES) -> AES-256-GCM.
     - Legacy hashes (MD5, SHA-1) -> SHA-256 or SHA-384.

3. **Deterministic Agility Cost Delta Model**:
   - Evaluated public key size ratio, ciphertext/signature overhead ratio, and CPU overhead delta.
   - Accurately computes `RiskCost` (`low`, `medium`, `high`) matching migration complexity.

4. **Integration**:
   - Exposed via `GET /api/v1/catalog/pqc` populated directly from `NIST_PQC_CATALOG`.
   - Verified in `backend/tests/test_pqc_catalog.py`.

## Consequences

- Recommendations and migration costs are strictly deterministic, standard-backed, and explainable to security compliance auditors.
- No dynamic external API calls or non-deterministic ML models used.
