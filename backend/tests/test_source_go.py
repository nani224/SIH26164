"""Tests for tree-sitter Go crypto usage detection."""

from __future__ import annotations

from api.models import CryptoFunction, Family
from engine.source_go import detect_code


def test_go_rsa_keygen_detection() -> None:
    code = b"""
    package main
    import (
        "crypto/rand"
        "crypto/rsa"
    )
    func main() {
        key, _ := rsa.GenerateKey(rand.Reader, 2048)
        _ = key
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.RSA
    assert d.function == CryptoFunction.KEYGEN
    assert d.key_size == 2048
    assert d.symbol == "rsa.GenerateKey"


def test_go_aes_cipher_detection() -> None:
    code = b"""
    package main
    import "crypto/aes"
    func initCipher(key []byte) {
        c, _ := aes.NewCipher(key)
        _ = c
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.AES
    assert detections[0].function == CryptoFunction.ENCRYPT


def test_go_hashes_and_ciphers() -> None:
    code = b"""
    package main
    import (
        "crypto/md5"
        "crypto/sha1"
        "crypto/sha256"
        "crypto/des"
    )
    func run() {
        _ = md5.New()
        _ = sha1.New()
        _ = sha256.Sum256([]byte("data"))
        _ = des.NewTripleDESCipher([]byte("key123456789012345678901"))
    }
    """
    detections = detect_code(code)
    families = [d.family for d in detections]
    assert Family.MD5 in families
    assert Family.SHA_1 in families
    assert Family.SHA_2 in families
    assert Family.THREE_DES in families


def test_go_hmac_with_underlying_hash() -> None:
    code = b"""
    package main
    import (
        "crypto/hmac"
        "crypto/sha256"
    )
    func tag(key []byte) {
        mac := hmac.New(sha256.New, key)
        _ = mac
    }
    """
    detections = detect_code(code)
    assert len(detections) >= 1
    hmac_d = [d for d in detections if d.family == Family.HMAC][0]
    assert hmac_d.underlying_hash_family == Family.SHA_2


def test_go_hmac_hash_argument_is_not_double_counted() -> None:
    # M6 regression: sha256.New passed as hmac.New's hash-constructor
    # argument is already captured via underlying_hash_family -- it must
    # not ALSO produce a separate standalone bare-reference finding on
    # the same line.
    code = b"""
    package main
    import (
        "crypto/hmac"
        "crypto/sha256"
    )
    func tag(key []byte) {
        mac := hmac.New(sha256.New, key)
        _ = mac
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.HMAC


def test_go_bare_function_reference_struct_field() -> None:
    # M6: a function VALUE assigned to a struct field, never called at
    # this call site -- e.g. gorilla/securecookie's `hashFunc: sha256.New,`.
    code = b"""
    package main
    import "crypto/sha256"
    type S struct { hashFunc func() hash.Hash }
    func New() *S {
        return &S{
            hashFunc: sha256.New,
        }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.SHA_2
    assert detections[0].function == CryptoFunction.DIGEST


def test_go_bare_function_reference_call_argument() -> None:
    # M6: a function VALUE passed as a bare argument, never called --
    # e.g. gorilla/securecookie's `s.BlockFunc(aes.NewCipher)`.
    code = b"""
    package main
    import "crypto/aes"
    func run(s *Wrapper) {
        s.BlockFunc(aes.NewCipher)
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.AES
    assert detections[0].function == CryptoFunction.ENCRYPT


def test_go_bare_reference_unrecognized_package_not_flagged() -> None:
    # An unrelated pkg.Func reference (not in any lookup table) must not
    # be force-labelled -- no guessing.
    code = b"""
    package main
    func run() {
        callback := strings.ToUpper
        _ = callback
    }
    """
    assert detect_code(code) == []
