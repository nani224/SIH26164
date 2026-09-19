from __future__ import annotations

from api.models import CryptoFunction, Family
from engine.source_python import detect


def _families(source: bytes) -> list[tuple[int, Family | None, CryptoFunction]]:
    return [(d.line or -1, d.family, d.function) for d in detect("t.py", source)]


def test_hashlib_direct_digest() -> None:
    src = b'hashlib.md5(b"x")\nhashlib.sha1(b"x")\nhashlib.sha256(b"x")\n'
    assert _families(src) == [
        (1, Family.MD5, CryptoFunction.DIGEST),
        (2, Family.SHA_1, CryptoFunction.DIGEST),
        (3, Family.SHA_2, CryptoFunction.DIGEST),
    ]


def test_hashlib_new() -> None:
    src = b'hashlib.new("sha1")\n'
    assert _families(src) == [(1, Family.SHA_1, CryptoFunction.DIGEST)]


def test_hashlib_new_unsupported_algorithm_is_not_flagged() -> None:
    src = b'hashlib.new("blake2b")\n'
    assert detect("t.py", src) == []


def test_hmac_new_captures_underlying_hash() -> None:
    src = b"hmac.new(key, msg, hashlib.sha1)\n"
    detections = detect("t.py", src)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.HMAC
    assert d.function == CryptoFunction.TAG
    assert d.underlying_hash_family == Family.SHA_1


def test_rsa_keygen_captures_key_size() -> None:
    src = b"rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    detections = detect("t.py", src)
    assert len(detections) == 1
    assert detections[0].family == Family.RSA
    assert detections[0].key_size == 2048


def test_ec_keygen_captures_curve_and_does_not_double_count() -> None:
    src = b"ec.generate_private_key(ec.SECP256R1())\n"
    detections = detect("t.py", src)
    assert len(detections) == 1
    assert detections[0].family == Family.ECDSA
    assert detections[0].curve == "SECP256R1"


def test_weak_ciphers() -> None:
    src = b"algorithms.TripleDES(key)\nalgorithms.ARC4(key)\nalgorithms.Blowfish(key)\n"
    assert _families(src) == [
        (1, Family.THREE_DES, CryptoFunction.ENCRYPT),
        (2, Family.RC4, CryptoFunction.ENCRYPT),
        (3, Family.BLOWFISH, CryptoFunction.ENCRYPT),
    ]


def test_aes_and_chacha20_are_detected_as_true_positives() -> None:
    src = b"algorithms.AES(key)\nalgorithms.ChaCha20(key, nonce)\n"
    assert _families(src) == [
        (1, Family.AES, CryptoFunction.ENCRYPT),
        (2, Family.CHACHA20, CryptoFunction.ENCRYPT),
    ]


def test_unrelated_calls_are_not_flagged() -> None:
    src = b'logging.info("hi")\nos.path.join("a", "b")\njson.dumps({})\n'
    assert detect("t.py", src) == []


def test_bare_identifier_calls_are_not_flagged() -> None:
    src = b"print(x)\nlen(y)\n"
    assert detect("t.py", src) == []


def test_bare_attribute_reference_detected() -> None:
    src = b"signer = Signer(digest_method=hashlib.sha256)\nalgo = hashlib.md5\n"
    detections = detect("t.py", src)
    assert len(detections) == 2
    assert detections[0].family == Family.SHA_2
    assert detections[1].family == Family.MD5


def test_key_sign_verify_resolved_via_parameter_type_annotation() -> None:
    # M4 (Track CC): a `key.sign(...)`/`key.verify(...)` call where `key`'s
    # concrete cryptography-library type is named in the enclosing
    # function's own parameter annotation -- a real, static fact, not a
    # guess. Closes the largest false-negative cluster found in the
    # real-world HOLD corpus (pyjwt's OO Algorithm classes).
    src = (
        b"def sign(self, msg: bytes, key: RSAPrivateKey) -> bytes:\n"
        b"    return key.sign(msg, padding.PKCS1v15(), hashes.SHA256())\n"
        b"def verify(self, msg: bytes, key: RSAPublicKey, sig: bytes) -> bool:\n"
        b"    return key.verify(sig, msg, padding.PKCS1v15(), hashes.SHA256())\n"
        b"def ec_sign(self, msg: bytes, key: EllipticCurvePrivateKey) -> bytes:\n"
        b"    return key.sign(msg, ec.ECDSA(hashes.SHA256()))\n"
        b"def ed_sign(self, msg: bytes, key: Ed25519PrivateKey | Ed448PrivateKey) -> bytes:\n"
        b"    return key.sign(msg)\n"
    )
    detections = detect("t.py", src)
    assert len(detections) == 4
    assert (detections[0].family, detections[0].function) == (Family.RSA, CryptoFunction.SIGN)
    assert (detections[1].family, detections[1].function) == (Family.RSA, CryptoFunction.VERIFY)
    assert (detections[2].family, detections[2].function) == (Family.ECDSA, CryptoFunction.SIGN)
    assert (detections[3].family, detections[3].function) == (Family.ED25519, CryptoFunction.SIGN)


def test_key_sign_verify_unresolvable_type_alias_is_not_flagged() -> None:
    # A project-specific type alias (e.g. pyjwt's own
    # `AllowedECKeys = Union[EllipticCurvePrivateKey, EllipticCurvePublicKey]`)
    # is a real, honest miss -- the detector must not guess, and must not
    # be hardcoded to recognize one specific project's alias name.
    src = b"def verify(self, msg: bytes, key: AllowedECKeys, sig: bytes) -> bool:\n    return key.verify(sig, msg)\n"
    assert detect("t.py", src) == []


def test_sign_verify_on_untyped_or_unrelated_parameter_is_not_flagged() -> None:
    # No type annotation at all, or an annotation that isn't a recognized
    # cryptography-library key class -- must not fire (no guessing).
    src = (
        b"def f(self, key, msg: bytes) -> bytes:\n"
        b"    return key.sign(msg)\n"
        b"def g(self, doc: PdfDocument) -> bytes:\n"
        b"    return doc.sign()\n"
    )
    assert detect("t.py", src) == []
