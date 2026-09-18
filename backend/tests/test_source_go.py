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
