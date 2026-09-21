"""Attribution calculus package for ECDAT CMC Engine.

Provides:
- claim: interval overlap join
- exclude: falsifiable exclusion predicates
- ledger: conservation invariant and residue clustering
"""

from __future__ import annotations

from engine.attribute.claim import attribute_claims, spans_overlap
from engine.attribute.exclude import (
    BENIGN_TABLE_HASHES,
    ExclusionRecord,
    evaluate_exclusions,
    is_identity_byte_table,
    is_media_or_plain_text_base64,
)
from engine.attribute.ledger import (
    AttributionLedger,
    ClusterState,
    ResidueCluster,
    cluster_residue_spans,
    compute_ledger,
)

__all__ = [
    "BENIGN_TABLE_HASHES",
    "AttributionLedger",
    "ClusterState",
    "ExclusionRecord",
    "ResidueCluster",
    "attribute_claims",
    "cluster_residue_spans",
    "compute_ledger",
    "evaluate_exclusions",
    "is_identity_byte_table",
    "is_media_or_plain_text_base64",
    "spans_overlap",
]
