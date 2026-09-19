from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the real-world (unseen, hand-labelled) sample
    in bench/real_world/ -- see its README for what this is (and isn't)
    before trusting these numbers as a general accuracy claim.

    Measured 2026-09-19 after growing the corpus to 5 files / 25 usages:
    precision 1.0 (zero false positives -- the detector never hallucinates
    crypto that isn't there), recall 0.52 (13/25 -- every miss is a bare
    attribute reference or an OO `key.sign()`/`key.verify()`/generic
    `cipher.Block` call needing intra-file type inference the engine
    doesn't have yet, both real, already-documented gaps in this
    directory's README, not new surprises). This is a floor, not a
    target: it must not regress below this, but 0.52 recall is itself the
    honest current number, not something to chase back up to 1.0 by
    weakening the corpus or the labels.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 0.52
    assert result["false_positives"] == []
    assert result["truth_count"] == 25
    assert result["detected_count"] == 13
