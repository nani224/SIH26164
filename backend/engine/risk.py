"""Pure Mosca risk-scoring formula (see backend/CLAUDE.md for the ADR-locked rule).

Score = 100 x V x F x U x E x K ; M = X + Y - Z
U = clamp(0.5 + M / (2*Z), 0.05, 1) ; U = 1 if classically broken
Bands: critical >= 60, high 35-59, medium 15-34, low < 15

This module is *only* the scoring math -- introduced early to back the
Phase 0 `/rescore` stub endpoint with something real instead of canned
numbers. It does not derive V/F/E/K from actual signals; that derivation
is part of the Phase 1+ engine (source/binary/artefact detectors feeding
engine.recommend / the rest of engine.risk).
"""

from __future__ import annotations

from typing import Literal

RiskBand = Literal["critical", "high", "medium", "low"]

_CRITICAL = 60.0
_HIGH = 35.0
_MEDIUM = 15.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_urgency(x: float, y: float, z: float, classically_broken: bool) -> float:
    if classically_broken:
        return 1.0
    margin = x + y - z
    return clamp(0.5 + margin / (2 * z), 0.05, 1.0)


def compute_score(v: float, f: float, e: float, k: float, u: float) -> float:
    return clamp(100.0 * v * f * u * e * k, 0.0, 100.0)


def band_for_score(score: float) -> RiskBand:
    if score >= _CRITICAL:
        return "critical"
    if score >= _HIGH:
        return "high"
    if score >= _MEDIUM:
        return "medium"
    return "low"


def rescore(
    *,
    v: float,
    f: float,
    e: float,
    k: float,
    x: float,
    y: float,
    z: float,
    classically_broken: bool,
) -> tuple[float, float, RiskBand]:
    """Returns (score, urgency, band) for the given factors and horizon Z."""
    u = compute_urgency(x, y, z, classically_broken)
    score = compute_score(v, f, e, k, u)
    return score, u, band_for_score(score)
