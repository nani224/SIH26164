from __future__ import annotations

from bench.real_world.evaluate import evaluate


def test_real_world_sample_detected_correctly() -> None:
    """Regression floor for the real-world (unseen, hand-labelled) sample
    in bench/real_world/ -- see its README for what this is (and isn't)
    before trusting these numbers as a general accuracy claim.

    Measured 2026-09-20 (M7, Track CC) after growing the corpus from 32 to
    56 usages (9 to 14 files): precision 0.9583 (2 false positives -- both
    real `aes.NewCipher(key)` calls in `x_crypto_ssh_keys.go` that the
    detector correctly finds, but that this corpus's own blind labeller
    chose to attribute to a downstream call instead; see
    docs/decisions/backend/019-m7-corpus-growth-and-aes-attribution.md
    for why the labels were NOT retroactively edited to "fix" this), still
    above the 0.95 floor enforced by bench/check_precision_floor.py.
    Recall 0.8214 (46/56, down from 0.875 purely because the corpus grew
    faster than detector coverage -- 28/32 old usages are still all
    found). 10 misses total: the 4 pre-existing ones (2 Go `cipher.NewCTR`
    generic-interface, 2 pyjwt type-alias/local-variable gaps, unchanged),
    3 more instances of that same Go generic-cipher-interface gap in
    `x_crypto_ssh_keys.go`, and 3 new gap categories found this pass (no
    Python PBKDF2 API coverage, one attribute-bound hash resolution case)
    -- see the README's numbered gap list for detail on all ten. This is a
    floor, not a target: it must not regress below this, but the honest
    number moved because the corpus got harder, not because anything
    broke.
    """
    result = evaluate()
    assert result["precision"] == 0.9583
    assert result["recall"] == 0.8214
    assert len(result["false_positives"]) == 2
    assert result["truth_count"] == 56
    assert result["detected_count"] == 48
