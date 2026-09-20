"""M1 Verification: Span provenance tests.

Verifies:
1. 100% of findings on the bench corpus carry at least one span.
2. Coarse-span rate is reported.
3. Property test: every span satisfies 0 <= span.start <= span.end <= len(artifact).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api.models import Context, Criticality, Exposure, Policy
from engine import source_c, source_go, source_java, source_python
from engine.models import Span
from engine.scanner import scan

BENCH_FIXTURES = Path(__file__).parent.parent / "bench" / "fixtures"
_POLICY = Policy(
    id="p",
    name="p",
    crqcYears=10,
    default=Context(
        exposure=Exposure.INTERNAL,
        criticality=Criticality.MEDIUM,
        shelfLifeYears=5,
        migrationYears=3,
    ),
    contexts=[],
)


def test_bench_corpus_100_percent_span_coverage(capsys: pytest.CaptureFixture[str]) -> None:
    """Every finding produced across the bench fixtures must carry >= 1 span."""
    result = scan(BENCH_FIXTURES, _POLICY)
    assert len(result.findings) > 0, "Bench fixtures produced no findings!"

    total_findings = len(result.findings)
    findings_with_spans = 0
    total_spans = 0
    coarse_spans = 0

    for finding in result.findings:
        spans: list[Span] = getattr(finding, "spans", [])
        if not spans:
            spans = result.spans_by_finding.get(finding.id, [])
        assert len(spans) >= 1, f"Finding {finding.id} ({finding.displayName}) has no spans!"
        findings_with_spans += 1
        for s in spans:
            total_spans += 1
            if s.coarse:
                coarse_spans += 1

    coverage_rate = findings_with_spans / total_findings
    coarse_rate = coarse_spans / total_spans if total_spans > 0 else 0.0

    print(f"\n[M1 Span Provenance Report]")
    print(f"  Total findings: {total_findings}")
    print(f"  Findings with spans: {findings_with_spans} ({coverage_rate * 100:.1f}%)")
    print(f"  Total spans: {total_spans}")
    print(f"  Coarse spans: {coarse_spans} (coarse rate: {coarse_rate * 100:.1f}%)")

    assert coverage_rate == 1.0, f"Span coverage is {coverage_rate * 100:.1f}%, expected 100%"


def test_span_bounds_on_all_bench_fixtures() -> None:
    """Verify that every span's range lies strictly within its artifact's bounds."""
    for fixture in BENCH_FIXTURES.iterdir():
        if not fixture.is_file():
            continue
        content = fixture.read_bytes()
        artifact_hash = hashlib.sha256(content).hexdigest()
        ext = fixture.suffix

        detections = []
        if ext == ".py":
            detections = source_python.detect(fixture.name, content, artifact_hash)
        elif ext == ".go":
            detections = source_go.detect_code(content, fixture.name, artifact_hash)
        elif ext == ".java":
            detections = source_java.detect_code(content, fixture.name, artifact_hash)
        elif ext in {".c", ".h", ".cpp", ".cc"}:
            detections = source_c.detect_code(content, fixture.name, artifact_hash)

        for det in detections:
            assert len(det.spans) >= 1, f"Detection {det.display_name} in {fixture.name} has no spans!"
            for span in det.spans:
                assert span.artifact_hash == artifact_hash
                assert 0 <= span.start, f"Negative span start {span.start} in {fixture.name}"
                assert span.start <= span.end, f"span.start ({span.start}) > span.end ({span.end}) in {fixture.name}"
                assert span.end <= len(content), (
                    f"span.end ({span.end}) exceeds file length ({len(content)}) in {fixture.name}"
                )
                assert span.producing_rule != "", f"Empty producing_rule in {fixture.name}"


@given(
    code=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        max_size=2000,
    )
)
@settings(max_examples=50)
def test_property_python_span_bounds(code: str) -> None:
    """Property test: for any arbitrary python source, all spans lie within bounds."""
    source_bytes = code.encode("utf-8")
    artifact_hash = hashlib.sha256(source_bytes).hexdigest()
    detections = source_python.detect("prop.py", source_bytes, artifact_hash)
    for det in detections:
        for span in det.spans:
            assert 0 <= span.start <= span.end <= len(source_bytes)
            assert span.artifact_hash == artifact_hash


@given(
    code=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        max_size=2000,
    )
)
@settings(max_examples=50)
def test_property_c_span_bounds(code: str) -> None:
    """Property test: for any arbitrary C source, all spans lie within bounds."""
    source_bytes = code.encode("utf-8")
    artifact_hash = hashlib.sha256(source_bytes).hexdigest()
    detections = source_c.detect_code(source_bytes, "prop.c", artifact_hash)
    for det in detections:
        for span in det.spans:
            assert 0 <= span.start <= span.end <= len(source_bytes)
            assert span.artifact_hash == artifact_hash
