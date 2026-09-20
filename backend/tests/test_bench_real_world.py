from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the real-world (unseen, hand-labelled) sample
    in bench/real_world/ -- see its README for what this is (and isn't)
    before trusting these numbers as a general accuracy claim.

    Measured 2026-09-20 (M6, Track CC) after closing the Go bare-
    function-reference cluster: precision 1.0 (zero false positives --
    see docs/decisions/backend/018-go-bare-function-reference.md for the
    M6 fix below and its own false-positive guard), recall 0.875 (28/32,
    up from 0.8125 -- closed Go's `hashFunc: sha256.New,` and
    `s.BlockFunc(aes.NewCipher)` pattern: a function VALUE referenced
    without being called, ported from the equivalent Python
    `attr.node` fix). Remaining 4 misses: two `gorilla_securecookie.go`
    `cipher.NewCTR(block, iv)` calls where `block` is a generic
    `cipher.Block` interface parameter (the concrete `aes.NewCipher`
    construction is several calls removed -- needs real dataflow, not
    attempted), one pyjwt `verify()` call whose key type comes from a
    project-specific type alias (`AllowedECKeys`, deliberately not
    hardcoded -- see ADR 016), and one pyjwt `verify()` call on a local
    variable rather than a typed parameter (needs real dataflow, not
    just signature inspection). This is a floor, not a target: it must
    not regress below this, but 0.875 recall is itself the honest
    current number, not something to chase back up by weakening the
    corpus or the labels.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 0.875
    assert result["false_positives"] == []
    assert result["truth_count"] == 32
    assert result["detected_count"] == 28
