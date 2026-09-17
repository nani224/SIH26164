"""Engine-local result types.

Reuses api.models.Finding/ScanStats directly rather than duplicating their
~15 fields into parallel engine-only types -- those are generic value
objects (kind/family/location/risk/...), not HTTP-layer concerns. Note:
this means engine/ currently depends on api/ for shared vocabulary enums
(Family, FindingKind, ...), which is backwards from a clean-architecture
standpoint (api should depend on engine, not vice versa). That dependency
direction was set by Phase 0 (api.models is where the contract-driven
enums live) and is accepted as debt for now -- see backend/LEARNINGS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from api.models import CryptoFunction, Family, Finding, FindingKind, FindingSource, ScanStats, Surface


@dataclass
class Detection:
    """A single raw hit from a language detector, before risk scoring / recommendation."""

    kind: FindingKind
    surface: Surface
    family: Family | None
    display_name: str
    function: CryptoFunction
    path: str
    line: int | None
    symbol: str
    snippet: str
    source: FindingSource
    confidence: float
    key_size: int | None = None
    mode: str | None = None
    curve: str | None = None
    underlying_hash_family: Family | None = None  # set for HMAC, drives V derivation


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    stats: ScanStats = field(
        default_factory=lambda: ScanStats(
            files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0
        )
    )
