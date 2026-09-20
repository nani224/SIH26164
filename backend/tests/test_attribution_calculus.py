"""M3 Verification: Attribution calculus tests.

Verifies:
1. Conservation invariant holds as a property test on every corpus artifact:
   attributed + excluded + residue == total, no unit lost.
2. Cluster hashes are stable across multiple runs.
3. Falsifiable exclusion registry properly excludes registered benign tables and records reasons.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from engine import source_c, source_go, source_java, source_python
from engine.attribute import compute_ledger
from engine.attribute.exclude import _CRC32_TABLE_BYTES, _CRC32_TABLE_HASH
from engine.extract import extract_all
from engine.models import Span

BENCH_FIXTURES = Path(__file__).parent.parent / "bench" / "fixtures"


def test_conservation_invariant_on_all_corpus_artifacts() -> None:
    """The conservation invariant must hold on 100% of artifacts in the corpus."""
    fixture_count = 0
    total_suspicion_mass_all = 0.0
    total_attributed_mass_all = 0.0
    total_excluded_mass_all = 0.0
    total_residue_mass_all = 0.0

    for fixture in sorted(BENCH_FIXTURES.iterdir()):
        if not fixture.is_file():
            continue
        content = fixture.read_bytes()
        artifact_hash = hashlib.sha256(content).hexdigest()
        ext = fixture.suffix

        # 1. Rule detections
        finding_spans: list[Span] = []
        if ext == ".py":
            dets = source_python.detect(fixture.name, content, artifact_hash)
            for d in dets:
                finding_spans.extend(d.spans)
        elif ext == ".go":
            dets = source_go.detect_code(content, fixture.name, artifact_hash)
            for d in dets:
                finding_spans.extend(d.spans)
        elif ext == ".java":
            dets = source_java.detect_code(content, fixture.name, artifact_hash)
            for d in dets:
                finding_spans.extend(d.spans)
        elif ext in {".c", ".h", ".cpp", ".cc"}:
            dets = source_c.detect_code(content, fixture.name, artifact_hash)
            for d in dets:
                finding_spans.extend(d.spans)

        # 2. Rule-independent suspicion spans
        suspicion_spans = extract_all(content, fixture.name, artifact_hash)

        # 3. Compute ledger
        ledger = compute_ledger(content, finding_spans, suspicion_spans, artifact_hash)

        # Strict invariant verification
        assert ledger.verify_invariant(), (
            f"Invariant violated for {fixture.name}: "
            f"attributed={ledger.attributed_mass}, excluded={ledger.excluded_mass}, "
            f"residue={ledger.residue_mass}, total={ledger.total_suspicion_mass}"
        )
        assert (
            len(ledger.attributed_spans) + len(ledger.excluded_spans) + len(ledger.residue_spans)
            == len(suspicion_spans)
        ), f"Span count mismatch in {fixture.name}"

        fixture_count += 1
        total_suspicion_mass_all += ledger.total_suspicion_mass
        total_attributed_mass_all += ledger.attributed_mass
        total_excluded_mass_all += ledger.excluded_mass
        total_residue_mass_all += ledger.residue_mass

    print("\n[M3 Attribution Calculus Invariant Report]")
    print(f"  Corpus artifacts audited: {fixture_count}")
    print(f"  Total suspicion mass: {total_suspicion_mass_all:.2f}")
    print(f"  Attributed mass: {total_attributed_mass_all:.2f}")
    print(f"  Excluded mass: {total_excluded_mass_all:.2f}")
    print(f"  Residue mass: {total_residue_mass_all:.2f}")
    assert abs(
        (total_attributed_mass_all + total_excluded_mass_all + total_residue_mass_all)
        - total_suspicion_mass_all
    ) < 1e-6


def test_cluster_hash_stability() -> None:
    """Residue cluster hashes must be strictly identical across repeated runs."""
    content = b"header... " + bytes(range(256)) + b" ... " + b"while exp > 0:\n    exp >>= 1\n"
    artifact_hash = hashlib.sha256(content).hexdigest()

    suspicion_spans = extract_all(content, "test.py", artifact_hash)
    ledger1 = compute_ledger(content, [], suspicion_spans, artifact_hash)
    ledger2 = compute_ledger(content, [], suspicion_spans, artifact_hash)
    ledger3 = compute_ledger(content, [], suspicion_spans, artifact_hash)

    assert len(ledger1.residue_clusters) > 0
    hashes1 = [c.id for c in ledger1.residue_clusters]
    hashes2 = [c.id for c in ledger2.residue_clusters]
    hashes3 = [c.id for c in ledger3.residue_clusters]
    assert hashes1 == hashes2 == hashes3


def test_benign_crc32_table_exclusion() -> None:
    """Benign CRC-32 lookup table is excluded via registry and records audit trail."""
    artifact = b"data_prefix..." + _CRC32_TABLE_BYTES + b"...data_suffix"
    artifact_hash = hashlib.sha256(artifact).hexdigest()
    suspicion_spans = extract_all(artifact, "binary.bin", artifact_hash)

    ledger = compute_ledger(artifact, [], suspicion_spans, artifact_hash)
    # The CRC table span must be excluded, not residue
    assert any(rec.content_hash == _CRC32_TABLE_HASH for rec in ledger.exclusion_records)
    assert len(ledger.excluded_spans) >= 1
    assert ledger.excluded_mass > 0
    assert ledger.verify_invariant()


@given(
    spans_data=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=500),
            st.integers(min_value=1, max_value=500),
            st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        ),
        max_size=30,
    )
)
@settings(max_examples=50)
def test_property_conservation_invariant_random_spans(spans_data: list[tuple[int, int, float]]) -> None:
    """Hypothesis property test: conservation invariant holds for arbitrary span configurations."""
    content = b"A" * 1000
    artifact_hash = hashlib.sha256(content).hexdigest()

    suspicion_spans: list[Span] = []
    for start, length, magnitude in spans_data:
        end = min(1000, start + length)
        if start < end:
            suspicion_spans.append(
                Span(
                    artifact_hash=artifact_hash,
                    kind="byte",
                    start=start,
                    end=end,
                    producing_rule="test.suspicion",
                    signal_type="test",
                    magnitude=magnitude,
                )
            )

    # Dummy finding span
    finding_spans = [
        Span(
            artifact_hash=artifact_hash,
            kind="byte",
            start=100,
            end=300,
            producing_rule="test.finding",
        )
    ]

    ledger = compute_ledger(content, finding_spans, suspicion_spans, artifact_hash)
    assert ledger.verify_invariant()
    assert (
        len(ledger.attributed_spans) + len(ledger.excluded_spans) + len(ledger.residue_spans)
        == len(suspicion_spans)
    )
