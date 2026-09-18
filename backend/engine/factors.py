"""Derives a Risk (V/F/E/K/X/Y/Z + score/band) for a Detection under a Policy.

New in Phase 1 -- Phase 0 only had the pure formula (engine/risk.py). See
docs/decisions/backend/002-phase1-risk-factors.md for why each factor maps
where it does.
"""

from __future__ import annotations

import fnmatch

from api.models import Context, CryptoFunction, Family, Policy, Risk, RiskBand
from engine.families import is_classically_broken, vulnerability
from engine.models import Detection
from engine.risk import band_for_score, rescore

_FUNCTION_CRITICALITY: dict[CryptoFunction, float] = {
    CryptoFunction.KEYGEN: 0.9,
    CryptoFunction.SIGN: 0.85,
    CryptoFunction.DECRYPT: 0.85,
    CryptoFunction.KEYDERIVE: 0.8,
    CryptoFunction.ENCRYPT: 0.7,
    CryptoFunction.VERIFY: 0.6,
    CryptoFunction.TAG: 0.6,
    CryptoFunction.DIGEST: 0.5,
    CryptoFunction.UNKNOWN: 0.5,
}

_CRITICALITY_WEIGHT = {"mission-critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
_EXPOSURE_WEIGHT = {"external": 1.0, "internal": 0.6, "isolated": 0.3, "test": 0.1}

_PRIVATE_KEY_FLOOR = 90.0


def _matched_context(path: str, policy: Policy) -> Context:
    for ctx in policy.contexts:
        if fnmatch.fnmatch(path, ctx.glob):
            return ctx
    return policy.default


def _resolve_vulnerability(detection: Detection) -> tuple[float, bool]:
    if detection.family is None:
        return 0.5, False
    if detection.family == Family.HMAC and detection.underlying_hash_family is not None:
        family = detection.underlying_hash_family
    else:
        family = detection.family
    return vulnerability(family, detection.key_size), is_classically_broken(family)


def derive_risk(detection: Detection, policy: Policy) -> Risk:
    ctx = _matched_context(detection.path, policy)
    v, classically_broken = _resolve_vulnerability(detection)
    f = _FUNCTION_CRITICALITY[detection.function]
    k = _CRITICALITY_WEIGHT[ctx.criticality.value]
    e = _EXPOSURE_WEIGHT[ctx.exposure.value]
    x = float(ctx.shelfLifeYears)
    y = float(ctx.migrationYears)
    z = float(policy.crqcYears)

    score, u, band = rescore(v=v, f=f, e=e, k=k, x=x, y=y, z=z, classically_broken=classically_broken)
    reason = (
        f"{detection.family.value if detection.family else 'unknown'} "
        f"{detection.function.value} in a {ctx.exposure.value}-exposed, "
        f"{ctx.criticality.value}-criticality context (shelf-life {ctx.shelfLifeYears}y, "
        f"migration {ctx.migrationYears}y, CRQC horizon {policy.crqcYears}y)."
    )
    needs_review = detection.confidence < 0.75
    hndl = x > 0 and v > 0.5

    forced_private_key = (
        detection.kind == "key"
        and detection.function in (CryptoFunction.SIGN, CryptoFunction.DECRYPT, CryptoFunction.KEYDERIVE)
        and ctx.exposure != "test"
        and score < _PRIVATE_KEY_FLOOR
    )
    if forced_private_key:
        score = _PRIVATE_KEY_FLOOR
        band = band_for_score(score)
        reason = "Unencrypted private key outside a test path -- forced to score >= 90 per policy."

    return Risk(
        score=round(score, 2),
        band=RiskBand(band),
        V=v, F=f, U=round(u, 4), E=e, K=k, X=x, Y=y, Z=z,
        moscaMargin=x + y - z,
        reason=reason,
        classicallyBroken=classically_broken,
        hndl=hndl,
        needsReview=needs_review,
    )
