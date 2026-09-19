from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the real-world (unseen, hand-labelled) sample
    in bench/real_world/ -- see its README for what this is (and isn't)
    before trusting these numbers as a general accuracy claim.

    Measured 2026-09-19 (M3, Track CC) after growing the corpus to 9
    files / 32 usages / 4 languages (Python, Go, Java, C): precision 1.0
    (zero false positives -- the detector never hallucinates crypto that
    isn't there; this required a real fix mid-session, see
    docs/decisions/backend/015-openssl-evp-cipher-context-linkage.md, to
    an OpenSSL EVP_CIPHER_fetch heuristic that briefly regressed precision
    to 0.89 before being caught and fixed by this exact real-world run),
    recall 0.625 (20/32 -- misses are a Java JCA dispatcher class where
    the algorithm name is a caller-supplied variable rather than a
    literal (no cross-file dataflow), an mbedTLS EC keygen call the
    labeler correctly left unlabelled as family-ambiguous (so not even a
    detector gap), and the pre-existing Python OO
    `key.sign()`/`key.verify()` and Go bare-attribute-reference gaps
    documented in this directory's README). This is a floor, not a
    target: it must not regress below this, but 0.625 recall is itself
    the honest current number, not something to chase back up by
    weakening the corpus or the labels.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 0.625
    assert result["false_positives"] == []
    assert result["truth_count"] == 32
    assert result["detected_count"] == 20
