from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the real-world (unseen, hand-labelled) sample
    in bench/real_world/ -- see its README for what this is (and isn't)
    before trusting these numbers as a general accuracy claim.

    Measured 2026-09-19 (M4, Track CC) after closing the largest
    false-negative cluster: precision 1.0 (zero false positives -- see
    docs/decisions/backend/015-openssl-evp-cipher-context-linkage.md for
    the OpenSSL EVP_CIPHER_fetch fix that restored this to 1.0 in M3, and
    docs/decisions/backend/016-python-key-method-type-annotation.md for
    the M4 fix below, which added 6 new true positives without
    introducing any new false positive), recall 0.8125 (26/32, up from
    0.625 -- closed pyjwt's `key.sign()`/`key.verify()` cluster by
    resolving `key`'s family from a real static fact: the enclosing
    function's own parameter type annotation, e.g. `key: RSAPrivateKey`,
    not a guess or cross-file dataflow). Remaining 6 misses: a Java JCA
    dispatcher class where the algorithm name is a caller-supplied
    variable (no cross-file dataflow), an mbedTLS EC keygen call the
    labeler correctly left unlabelled as family-ambiguous, one pyjwt
    `verify()` call whose key type comes from a project-specific type
    alias (`AllowedECKeys`, deliberately not hardcoded -- see ADR 016),
    one pyjwt `verify()` call on a local variable rather than a typed
    parameter (needs real dataflow, not just signature inspection), and
    the pre-existing Go bare-attribute-reference gaps documented in this
    directory's README. This is a floor, not a target: it must not
    regress below this, but 0.8125 recall is itself the honest current
    number, not something to chase back up by weakening the corpus or
    the labels.
    """
    result = evaluate()
    assert result["precision"] == 1.0
    assert result["recall"] == 0.8125
    assert result["false_positives"] == []
    assert result["truth_count"] == 32
    assert result["detected_count"] == 26
