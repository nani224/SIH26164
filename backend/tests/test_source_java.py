"""Tests for tree-sitter Java crypto usage detection (M1, Track CC)."""

from __future__ import annotations

from api.models import CryptoFunction, Family
from engine.source_java import detect_code


def test_java_cipher_transformation_string_parsing() -> None:
    code = b"""
    public class C {
      void run() throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.AES
    assert d.function == CryptoFunction.ENCRYPT
    assert d.mode == "GCM"
    assert d.symbol == "Cipher.getInstance"


def test_java_keypairgenerator_linked_to_initialize_key_size() -> None:
    code = b"""
    public class K {
      void run() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.RSA
    assert d.function == CryptoFunction.KEYGEN
    assert d.key_size == 2048


def test_java_ec_keypairgenerator_linked_to_curve() -> None:
    code = b"""
    public class K {
      void run() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
        kpg.initialize(new ECGenParameterSpec("secp256r1"));
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.ECDSA
    assert d.function == CryptoFunction.KEYGEN
    assert d.curve == "secp256r1"


def test_java_keypairgenerator_without_initialize_still_detected() -> None:
    # No follow-up .initialize() call -- must still emit a finding (just
    # without key_size), not silently drop it while waiting for a link
    # that never comes.
    code = b"""
    public class K {
      void run() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.RSA
    assert detections[0].key_size is None


def test_java_message_digest() -> None:
    code = b"""
    public class D {
      void run() throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.SHA_2
    assert detections[0].function == CryptoFunction.DIGEST


def test_java_signature_transformation_string_parsing() -> None:
    code = b"""
    public class S {
      void run() throws Exception {
        Signature sig = Signature.getInstance("SHA256withRSA");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.RSA
    assert d.function == CryptoFunction.SIGN
    assert d.underlying_hash_family == Family.SHA_2


def test_java_mac_hmac_transformation_string_parsing() -> None:
    code = b"""
    public class M {
      void run() throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.HMAC
    assert d.function == CryptoFunction.TAG
    assert d.underlying_hash_family == Family.SHA_2


def test_java_keyagreement_ecdh() -> None:
    code = b"""
    public class A {
      void run() throws Exception {
        KeyAgreement ka = KeyAgreement.getInstance("ECDH");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.ECDH
    assert detections[0].function == CryptoFunction.KEYDERIVE


def test_java_secretkeyfactory_pbkdf2() -> None:
    # M7: found while sourcing a real HOLD candidate (Spring Security's
    # Pbkdf2PasswordEncoder) that uses SecretKeyFactory for key derivation.
    code = b"""
    public class P {
      void run() throws Exception {
        SecretKeyFactory f = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.HMAC
    assert detections[0].function == CryptoFunction.KEYDERIVE
    assert detections[0].underlying_hash_family == Family.SHA_2


def test_java_secretkeyfactory_non_pbkdf2_unmapped() -> None:
    # Legacy PBEWith... names intentionally unmapped -- no Family maps
    # cleanly onto a password-based-encryption transform, so don't guess.
    code = b"""
    public class P {
      void run() throws Exception {
        SecretKeyFactory f = SecretKeyFactory.getInstance("PBEWithMD5AndDES");
      }
    }
    """
    assert detect_code(code) == []


def test_java_secretkeyspec_key_material() -> None:
    code = b"""
    public class K {
      void run(byte[] key) {
        SecretKeySpec sks = new SecretKeySpec(key, "AES");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.AES
    assert detections[0].symbol == "new SecretKeySpec"


def test_java_sslcontext_tls_protocol_detected_without_family() -> None:
    code = b"""
    public class S {
      void run() throws Exception {
        SSLContext ssl = SSLContext.getInstance("TLSv1.2");
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family is None
    assert detections[0].symbol == "SSLContext.getInstance"


def test_java_bouncycastle_direct_class_usage() -> None:
    code = b"""
    public class B {
      void run() {
        SHA256Digest d = new SHA256Digest();
        AESEngine e = new AESEngine();
      }
    }
    """
    detections = detect_code(code)
    assert len(detections) == 2
    families = {d.family for d in detections}
    assert families == {Family.SHA_2, Family.AES}


def test_java_true_negatives_do_not_fire() -> None:
    # Common non-crypto object creations/calls that must NOT be misread as
    # crypto usages -- catches overmatching before it ever reaches the
    # precision floor.
    code = b"""
    public class N {
      void run() {
        StringBuilder sb = new StringBuilder();
        ArrayList<String> list = new ArrayList<>();
        Logger log = LoggerFactory.getLogger(N.class);
        sb.append("x");
        list.add("y");
      }
    }
    """
    detections = detect_code(code)
    assert detections == []
