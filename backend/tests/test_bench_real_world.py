from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the small real-world (unseen, hand-labelled)
    sample in bench/real_world/ -- see its README for what this is (and
    isn't) before trusting these numbers as a general accuracy claim.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert result["truth_count"] == 4
