"""Attribution claim calculus.

Joins finding spans against extractor suspicion spans via interval overlap.
A suspicion span is ATTRIBUTED when overlapped by >= 1 finding span on the same artifact.
"""

from __future__ import annotations

from engine.models import Span


def spans_overlap(s1: Span, s2: Span) -> bool:
    """Check if two spans on the same artifact overlap in range."""
    if s1.artifact_hash != s2.artifact_hash:
        return False
    # Standard interval overlap: max(start) < min(end)
    return max(s1.start, s2.start) < min(s1.end, s2.end)


def attribute_claims(
    finding_spans: list[Span],
    suspicion_spans: list[Span],
) -> tuple[list[Span], list[Span], dict[Span, list[Span]]]:
    """Join finding spans against suspicion spans.

    Returns:
        attributed: Suspicion spans overlapped by at least one finding span.
        unclaimed: Suspicion spans not overlapped by any finding span.
        overlap_map: Mapping from each attributed suspicion span to claiming finding spans.
    """
    attributed: list[Span] = []
    unclaimed: list[Span] = []
    overlap_map: dict[Span, list[Span]] = {}

    for s_span in suspicion_spans:
        matching_findings = [f_span for f_span in finding_spans if spans_overlap(s_span, f_span)]
        if matching_findings:
            attributed.append(s_span)
            overlap_map[s_span] = matching_findings
        else:
            unclaimed.append(s_span)

    return attributed, unclaimed, overlap_map
