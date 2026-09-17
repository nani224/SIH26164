from __future__ import annotations

from bench.evaluate import evaluate


def test_bench_starter_fixtures_are_fully_detected() -> None:
    """Regression floor: never let Phase 1's starter fixture set regress.

    Not the brief's Layer A/B corpus (see bench/README.md) -- just the
    small hand-built set that exists today.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert result["truth_count"] == 15
