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
from typing import Literal

from api.models import CryptoFunction, Family, Finding, FindingKind, FindingSource, ScanStats, Surface


@dataclass(frozen=True)
class Span:
    """A bounded evidence range within an artifact consumed by a detection rule or extractor."""

    artifact_hash: str
    kind: Literal["byte", "ast"]
    start: int
    end: int
    producing_rule: str = ""
    coarse: bool = False
    signal_type: str | None = None
    magnitude: float = 1.0

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"Span start must be >= 0, got {self.start}")
        if self.end < self.start:
            raise ValueError(f"Span end ({self.end}) must be >= start ({self.start})")

    @property
    def length(self) -> int:
        return self.end - self.start


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
    spans: list[Span] = field(default_factory=list)


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    stats: ScanStats = field(
        default_factory=lambda: ScanStats(
            files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0
        )
    )
    spans_by_finding: dict[str, list[Span]] = field(default_factory=dict)
