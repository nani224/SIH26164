from __future__ import annotations

from api.models import (
    Context,
    ContextWithGlob,
    Criticality,
    CryptoFunction,
    Exposure,
    Family,
    FindingKind,
    FindingSource,
    Policy,
    Surface,
)
from engine.factors import derive_risk
from engine.models import Detection


def _policy(**overrides: object) -> Policy:
    defaults: dict[str, object] = dict(
        exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3
    )
    defaults.update(overrides)
    return Policy(id="p", name="p", crqcYears=10, default=Context(**defaults), contexts=[])  # type: ignore[arg-type]


def _detection(**overrides: object) -> Detection:
    # function=SIGN, not KEYGEN: KEYGEN + a Shor-broken family (RSA's V=1.0)
    # trips the private-key >=90 floor (see engine/factors.py) outside a
    # test-exposure path, which would swamp every other factor these
    # generic tests are isolating. The two dedicated private-key-floor
    # tests below override function=KEYGEN explicitly.
    defaults: dict[str, object] = dict(
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.RSA,
        display_name="RSA signature",
        function=CryptoFunction.SIGN,
        path="app.py",
        line=1,
        symbol="private_key.sign",
        snippet="private_key.sign(...)",
        source=FindingSource.AST,
        confidence=0.9,
    )
    defaults.update(overrides)
    return Detection(**defaults)  # type: ignore[arg-type]


def test_rsa_is_flagged_high_vulnerability() -> None:
    risk = derive_risk(_detection(), _policy())
    assert risk.V == 1.0
    assert risk.classicallyBroken is False


def test_aes_256_has_low_vulnerability() -> None:
    d = _detection(family=Family.AES, function=CryptoFunction.ENCRYPT, key_size=256)
    risk = derive_risk(d, _policy())
    assert risk.V == 0.1


def test_aes_128_has_higher_vulnerability_than_aes_256() -> None:
    d128 = _detection(family=Family.AES, function=CryptoFunction.ENCRYPT, key_size=128)
    d256 = _detection(family=Family.AES, function=CryptoFunction.ENCRYPT, key_size=256)
    policy = _policy()
    assert derive_risk(d128, policy).V > derive_risk(d256, policy).V


def test_md5_is_classically_broken_and_forces_urgency_one() -> None:
    d = _detection(family=Family.MD5, function=CryptoFunction.DIGEST)
    risk = derive_risk(d, _policy())
    assert risk.classicallyBroken is True
    assert risk.U == 1.0


def test_hmac_uses_underlying_hash_vulnerability() -> None:
    weak = _detection(family=Family.HMAC, function=CryptoFunction.TAG, underlying_hash_family=Family.SHA_1)
    strong = _detection(family=Family.HMAC, function=CryptoFunction.TAG, underlying_hash_family=Family.SHA_2)
    policy = _policy()
    assert derive_risk(weak, policy).V > derive_risk(strong, policy).V


def test_context_glob_matching_picks_more_exposed_context() -> None:
    policy = Policy(
        id="p", name="p", crqcYears=10,
        default=Context(exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3),
        contexts=[
            ContextWithGlob(
                glob="**/prod/**", exposure=Exposure.EXTERNAL, criticality=Criticality.MISSION_CRITICAL,
                shelfLifeYears=10, migrationYears=5,
            ),
        ],
    )
    prod_detection = _detection(path="services/prod/app.py")
    default_detection = _detection(path="services/dev/app.py")
    assert derive_risk(prod_detection, policy).score > derive_risk(default_detection, policy).score


def test_needs_review_below_confidence_threshold() -> None:
    d = _detection(confidence=0.6)
    risk = derive_risk(d, _policy())
    assert risk.needsReview is True


def test_confident_finding_does_not_need_review() -> None:
    d = _detection(confidence=0.9)
    risk = derive_risk(d, _policy())
    assert risk.needsReview is False


def test_unencrypted_private_key_outside_test_path_is_forced_to_at_least_90() -> None:
    # function=KEYGEN + a Shor-broken family (V=1.0) is the real signal a
    # scan can actually produce today (see engine/factors.py's
    # forced_private_key comment) -- kind=KEY + function=SIGN/DECRYPT is
    # never emitted by any real detector, so this must exercise the
    # reachable path, not a hand-built one that can't occur in practice.
    d = _detection(
        kind=FindingKind.ALGORITHM, family=Family.RSA, function=CryptoFunction.KEYGEN, confidence=0.95,
        display_name="RSA key generation", symbol="rsa.generate_private_key", path="secrets/server_keygen.py",
    )
    policy = _policy(exposure=Exposure.INTERNAL, criticality=Criticality.LOW)
    risk = derive_risk(d, policy)
    assert risk.score >= 90.0
    assert risk.band == "critical"


def test_private_key_override_does_not_apply_in_test_paths() -> None:
    d = _detection(
        kind=FindingKind.ALGORITHM, family=Family.RSA, function=CryptoFunction.KEYGEN, confidence=0.95,
        display_name="RSA key generation", symbol="rsa.generate_private_key", path="tests/fixtures/server_keygen.py",
    )
    policy = _policy(exposure=Exposure.TEST, criticality=Criticality.LOW)
    risk = derive_risk(d, policy)
    assert risk.score < 90.0
