"""Tests for tree-sitter C/C++ crypto usage detection (M2, Track CC)."""

from __future__ import annotations

from api.models import CryptoFunction, Family
from engine.source_c import detect_code


def test_openssl_evp_cipher_fetch_algorithm_string_parsing() -> None:
    code = b'void f(){ EVP_CIPHER *c = EVP_CIPHER_fetch(NULL, "AES-256-GCM", NULL); }'
    detections = detect_code(code)
    assert len(detections) == 1
    d = detections[0]
    assert d.family == Family.AES
    assert d.function == CryptoFunction.ENCRYPT
    assert d.key_size == 256
    assert d.mode == "GCM"


def test_openssl_evp_md_fetch_digest_string_parsing() -> None:
    code = b'void f(){ EVP_MD *m = EVP_MD_fetch(NULL, "SHA256", NULL); }'
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.SHA_2
    assert detections[0].function == CryptoFunction.DIGEST


def test_openssl_rsa_keygen_bits() -> None:
    code = b"void f(EVP_PKEY_CTX *ctx){ EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 2048); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.RSA
    assert detections[0].function == CryptoFunction.KEYGEN
    assert detections[0].key_size == 2048


def test_openssl_ec_paramgen_curve_nid() -> None:
    code = b"void f(EVP_PKEY_CTX *ctx){ EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_X9_62_prime256v1); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.ECDSA
    assert detections[0].curve == "NID_X9_62_prime256v1"


def test_openssl_legacy_zero_arg_algorithm_getters() -> None:
    code = b"""
    void f(EVP_CIPHER_CTX *ctx, unsigned char *key, unsigned char *iv) {
        EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, key, iv);
        EVP_DigestInit_ex(ctx, EVP_sha1(), NULL);
    }
    """
    detections = detect_code(code)
    assert len(detections) == 2
    aes = next(d for d in detections if d.family == Family.AES)
    assert aes.key_size == 128
    assert aes.mode == "CBC"
    sha = next(d for d in detections if d.family == Family.SHA_1)
    assert sha.function == CryptoFunction.DIGEST


def test_mbedtls_aes_setkey_and_digest_starts() -> None:
    code = b"""
    void f(mbedtls_aes_context *aes, unsigned char *key, mbedtls_sha256_context *sha) {
        mbedtls_aes_setkey_enc(aes, key, 256);
        mbedtls_sha256_starts(sha);
    }
    """
    detections = detect_code(code)
    assert len(detections) == 2
    aes = next(d for d in detections if d.family == Family.AES)
    assert aes.function == CryptoFunction.ENCRYPT
    assert aes.key_size == 256


def test_mbedtls_rsa_and_ecdsa_keygen() -> None:
    code = b"""
    void f(mbedtls_rsa_context *rsa, mbedtls_ecdsa_context *ec, void *rng) {
        mbedtls_rsa_gen_key(rsa, rng, NULL, 3072, 65537);
        mbedtls_ecdsa_genkey(ec, MBEDTLS_ECP_DP_SECP256R1, rng, NULL);
    }
    """
    detections = detect_code(code)
    assert len(detections) == 2
    rsa = next(d for d in detections if d.family == Family.RSA)
    assert rsa.key_size == 3072
    ec = next(d for d in detections if d.family == Family.ECDSA)
    assert ec.curve == "MBEDTLS_ECP_DP_SECP256R1"


def test_wolfssl_aes_setkey_byte_to_bit_conversion() -> None:
    # wc_AesSetKey's len arg is in BYTES (wolfSSL API), unlike OpenSSL/
    # mbedTLS which pass bits directly -- key_size must come out as bits
    # (32 bytes -> 256) for consistency with the rest of the engine.
    code = b"void f(Aes *aes, byte *key, byte *iv){ wc_AesSetKey(aes, key, 32, iv, AES_ENCRYPTION); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.AES
    assert detections[0].function == CryptoFunction.ENCRYPT
    assert detections[0].key_size == 256


def test_wolfssl_aes_setkey_decrypt_direction() -> None:
    code = b"void f(Aes *aes, byte *key, byte *iv){ wc_AesSetKey(aes, key, 16, iv, AES_DECRYPTION); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].function == CryptoFunction.DECRYPT


def test_wolfssl_make_rsa_key() -> None:
    code = b"void f(RsaKey *k, WC_RNG *rng){ wc_MakeRsaKey(k, 2048, 65537, rng); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.RSA
    assert detections[0].key_size == 2048


def test_wolfssl_hmac_underlying_hash_not_confused_by_substring() -> None:
    # WC_SHA256 must resolve to SHA-2, not SHA-1 -- "SHA" and "SHA1" are
    # both substrings of "WCSHA256" once underscores are stripped, so the
    # underlying-hash lookup must prefer the longest matching name.
    code = b"void f(Hmac *h, byte *key, word32 sz){ wc_HmacSetKey(h, WC_SHA256, key, sz); }"
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.HMAC
    assert detections[0].underlying_hash_family == Family.SHA_2


def test_c_true_negatives_do_not_fire() -> None:
    code = b"""
    void f(void) {
        printf("hello, world\\n");
        void *buf = malloc(64);
        memcpy(buf, "data", 4);
        free(buf);
    }
    """
    detections = detect_code(code)
    assert detections == []


def test_cpp_class_wrapper_still_parses_calls() -> None:
    # A C++ class wrapper around a plain OpenSSL call -- the C grammar
    # locally recovers around class/access-specifier syntax it doesn't
    # know and still finds the call expression inside.
    code = b"""
    class CipherWrapper {
    public:
      void encrypt(EVP_CIPHER_CTX *ctx, unsigned char *key, unsigned char *iv) {
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv);
      }
    };
    """
    detections = detect_code(code)
    assert len(detections) == 1
    assert detections[0].family == Family.AES
    assert detections[0].key_size == 256
