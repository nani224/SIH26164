from __future__ import annotations

from bench.evaluate import evaluate


def test_bench_starter_fixtures_are_fully_detected() -> None:
    """Regression floor: never let the starter fixture set regress.

    Not the brief's Layer A/B corpus (see bench/README.md) -- just the
    hand-built set. Grew from 15 (Python-only) to 40 (Java, M1) to 56
    (C/C++, M2) to 62 (Go sign/verify, M7) to 64 (Java SecretKeyFactory, M7)
    to 331 usages across 6 languages in M7; still fully detected.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert result["truth_count"] == 331

