"""Per-family quantum-vulnerability table (the V factor) and classical-break flags.

Deterministic and hand-derived from public cryptanalysis results (Shor's
algorithm breaks discrete-log/factoring in poly time; Grover's algorithm
only square-roots a symmetric cipher's or hash's effective security).
Nothing here is measured or tuned -- it's a fixed lookup, changeable only
with an ADR (see docs/decisions/backend/002-phase1-risk-factors.md).
"""

from __future__ import annotations

from api.models import Family

# Shor-vulnerable asymmetric algorithms: broken in polynomial time by a
# cryptographically-relevant quantum computer regardless of key size.
_SHOR_BROKEN: frozenset[Family] = frozenset(
    {Family.RSA, Family.DSA, Family.DH, Family.ECDH, Family.ECDSA, Family.ED25519, Family.X25519}
)

# NIST-standardized post-quantum families: not vulnerable to the known
# quantum algorithms at their standardized parameter sets.
_POST_QUANTUM: frozenset[Family] = frozenset({Family.ML_KEM, Family.ML_DSA, Family.SLH_DSA})

# Already classically broken/deprecated regardless of quantum computers.
_CLASSICALLY_BROKEN: frozenset[Family] = frozenset(
    {Family.MD5, Family.SHA_1, Family.DES, Family.RC4, Family.THREE_DES}
)

_HASH_FAMILIES: frozenset[Family] = frozenset(
    {Family.MD5, Family.SHA_1, Family.SHA_2, Family.SHA_3}
)


def is_classically_broken(family: Family) -> bool:
    return family in _CLASSICALLY_BROKEN


def vulnerability(family: Family, key_size: int | None) -> float:
    """Returns V in [0, 1]: how exposed this algorithm is to a CRQC."""
    if family in _SHOR_BROKEN:
        return 1.0
    if family in _POST_QUANTUM:
        return 0.0
    if family in _CLASSICALLY_BROKEN:
        return 1.0
    if family == Family.BLOWFISH:
        return 1.0  # 64-bit block, deprecated regardless of quantum concerns
    if family in (Family.AES, Family.CHACHA20):
        # Grover halves effective security bits; 256-bit keys stay safe.
        if key_size is not None and key_size < 256:
            return 0.6
        return 0.1
    if family in _HASH_FAMILIES:
        # SHA-2/SHA-3: Grover halves preimage-resistance bits; 256+ bit
        # digests remain comfortably secure.
        return 0.05
    if family == Family.HMAC:
        # Caller should resolve the underlying hash and call vulnerability()
        # on that instead; this is only a fallback for an unresolved HMAC.
        return 0.05
    return 0.5  # unknown family: neutral, needsReview will catch it via low confidence
