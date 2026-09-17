"""Filtering/sorting/pagination for GET /scans/{id}/findings.

Operates over whatever finding list it's given (Phase 0: the fixed stub
set). The filtering logic itself is real and reusable once Phase 2 wires it
to a persisted findings table.
"""

from __future__ import annotations

from api.models import BandCounts, Finding, FindingPage


def filter_findings(
    findings: list[Finding],
    *,
    band: str | None = None,
    family: str | None = None,
    surface: str | None = None,
    source: str | None = None,
    min_confidence: float | None = None,
    needs_review: bool | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> list[Finding]:
    result = findings
    if band is not None:
        result = [f for f in result if f.risk is not None and f.risk.band == band]
    if family is not None:
        result = [f for f in result if f.family == family]
    if surface is not None:
        result = [f for f in result if f.surface == surface]
    if source is not None:
        result = [f for f in result if f.source == source]
    if min_confidence is not None:
        result = [f for f in result if f.confidence >= min_confidence]
    if needs_review is not None:
        result = [f for f in result if f.risk is not None and f.risk.needsReview == needs_review]
    if q:
        ql = q.lower()
        result = [
            f
            for f in result
            if ql in f.displayName.lower()
            or ql in f.symbol.lower()
            or ql in f.snippet.lower()
            or ql in f.location.path.lower()
        ]
    if sort == "score":
        result = sorted(result, key=lambda f: f.risk.score if f.risk else -1.0, reverse=True)
    elif sort == "path":
        result = sorted(result, key=lambda f: f.location.path)
    elif sort == "family":
        result = sorted(result, key=lambda f: f.family or "")
    return result


def band_counts(findings: list[Finding]) -> BandCounts:
    counts = BandCounts()
    for f in findings:
        if f.risk is None:
            continue
        setattr(counts, f.risk.band, getattr(counts, f.risk.band) + 1)
    return counts


def paginate(findings: list[Finding], *, cursor: str | None, limit: int) -> FindingPage:
    offset = int(cursor) if cursor else 0
    page = findings[offset : offset + limit]
    next_cursor = str(offset + limit) if offset + limit < len(findings) else None
    return FindingPage(items=page, cursor=next_cursor, total=len(findings))
