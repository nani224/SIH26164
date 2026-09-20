"""Attribution ledger and residue clustering.

Computes the Conservation Invariant:
    attributed + excluded + residue == total_suspicion_mass (per artifact)

Residue clusters are keyed by content hash for cross-artifact stability.
Cluster states: open | promoted-to-rule | excluded | accepted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from engine.attribute.claim import attribute_claims
from engine.attribute.exclude import ExclusionRecord, evaluate_exclusions
from engine.models import Span

ClusterState = Literal["open", "promoted-to-rule", "excluded", "accepted"]


@dataclass
class ResidueCluster:
    id: str  # SHA-256 hash of cluster slice bytes for cross-artifact recognisability
    artifact_hash: str
    start: int
    end: int
    mass: float
    spans: list[Span]
    state: ClusterState = "open"
    content_preview: str = ""
    owner: str | None = None
    justification: str | None = None


@dataclass(frozen=True)
class AttributionLedger:
    artifact_hash: str
    total_suspicion_mass: float
    attributed_mass: float
    excluded_mass: float
    residue_mass: float
    coverage_ratio: float
    attributed_spans: list[Span]
    excluded_spans: list[Span]
    residue_spans: list[Span]
    residue_clusters: list[ResidueCluster]
    exclusion_records: list[ExclusionRecord]

    def verify_invariant(self) -> bool:
        """Verify the conservation invariant: attributed + excluded + residue == total."""
        accounted = self.attributed_mass + self.excluded_mass + self.residue_mass
        return abs(accounted - self.total_suspicion_mass) < 1e-6


def cluster_residue_spans(
    residue_spans: list[Span],
    artifact_content: bytes,
    artifact_hash: str,
    gap_threshold: int = 32,
) -> list[ResidueCluster]:
    """Cluster adjacent or overlapping residue spans into identifiable clusters."""
    if not residue_spans:
        return []

    sorted_spans = sorted(residue_spans, key=lambda s: (s.start, s.end))
    clusters: list[ResidueCluster] = []

    cur_start = sorted_spans[0].start
    cur_end = sorted_spans[0].end
    cur_spans = [sorted_spans[0]]

    for span in sorted_spans[1:]:
        if span.start <= cur_end + gap_threshold:
            cur_end = max(cur_end, span.end)
            cur_spans.append(span)
        else:
            slice_bytes = artifact_content[cur_start:cur_end]
            cluster_id = hashlib.sha256(slice_bytes).hexdigest()
            cluster_mass = sum(s.magnitude for s in cur_spans)
            preview = slice_bytes[:60].decode("latin1", errors="replace")
            clusters.append(
                ResidueCluster(
                    id=cluster_id,
                    artifact_hash=artifact_hash,
                    start=cur_start,
                    end=cur_end,
                    mass=cluster_mass,
                    spans=cur_spans,
                    content_preview=preview,
                )
            )
            cur_start = span.start
            cur_end = span.end
            cur_spans = [span]

    slice_bytes = artifact_content[cur_start:cur_end]
    cluster_id = hashlib.sha256(slice_bytes).hexdigest()
    cluster_mass = sum(s.magnitude for s in cur_spans)
    preview = slice_bytes[:60].decode("latin1", errors="replace")
    clusters.append(
        ResidueCluster(
            id=cluster_id,
            artifact_hash=artifact_hash,
            start=cur_start,
            end=cur_end,
            mass=cluster_mass,
            spans=cur_spans,
            content_preview=preview,
        )
    )

    return clusters


def compute_ledger(
    artifact_content: bytes,
    finding_spans: list[Span],
    suspicion_spans: list[Span],
    artifact_hash: str | None = None,
) -> AttributionLedger:
    """Compute attribution ledger and enforce the conservation invariant."""
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(artifact_content).hexdigest()

    # Total suspicion mass
    total_suspicion_mass = sum(s.magnitude for s in suspicion_spans)

    # 1. Claim calculus: join finding spans against suspicion spans
    attributed_spans, unclaimed_spans, _ = attribute_claims(finding_spans, suspicion_spans)
    attributed_mass = sum(s.magnitude for s in attributed_spans)

    # 2. Exclude calculus: evaluate falsifiable exclusion predicates
    excluded_spans, residue_spans, exclusion_records = evaluate_exclusions(
        unclaimed_spans, artifact_content
    )
    excluded_mass = sum(s.magnitude for s in excluded_spans)
    residue_mass = sum(s.magnitude for s in residue_spans)

    # Invariant: attributed + excluded + residue == total_suspicion_mass
    coverage_ratio = (
        attributed_mass / total_suspicion_mass if total_suspicion_mass > 0.0 else 1.0
    )

    # 3. Cluster residue spans
    residue_clusters = cluster_residue_spans(residue_spans, artifact_content, artifact_hash)

    ledger = AttributionLedger(
        artifact_hash=artifact_hash,
        total_suspicion_mass=total_suspicion_mass,
        attributed_mass=attributed_mass,
        excluded_mass=excluded_mass,
        residue_mass=residue_mass,
        coverage_ratio=coverage_ratio,
        attributed_spans=attributed_spans,
        excluded_spans=excluded_spans,
        residue_spans=residue_spans,
        residue_clusters=residue_clusters,
        exclusion_records=exclusion_records,
    )

    assert ledger.verify_invariant(), (
        f"Conservation invariant violated: {attributed_mass} + {excluded_mass} + {residue_mass} != {total_suspicion_mass}"
    )

    return ledger
