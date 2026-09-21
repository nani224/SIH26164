// Real-world Rust cryptographic usages using ring, aes-gcm, sha2, sha3, rsa, dalek, hmac.
// Permissive MIT/Apache-2.0 reference implementation.

use ring::aead::{AES_256_GCM, AES_128_GCM, CHACHA20_POLY1305};
use ring::digest::{SHA256, SHA384, SHA512, SHA1_FOR_LEGACY_USE_ONLY};
use ring::signature::{ED25519, RSA_PKCS1_2048_8192_SHA256};
use ring::agreement::{X25519, ECDH_P256, ECDH_P384};
use aes_gcm::{Aes256Gcm, Aes128Gcm};
use chacha20poly1305::ChaCha20Poly1305;
use sha2::{Sha256, Sha384, Sha512};
use sha3::{Sha3_256, Sha3_512};
use sha1::Sha1;
use md5::Md5;
use rsa::RsaPrivateKey;
use ed25519_dalek::SigningKey;
use hmac::Hmac;
use des::{Des, TripleDes};

pub fn ring_aead() {
    let _a1 = &AES_256_GCM;
    let _a2 = &AES_128_GCM;
    let _a3 = &CHACHA20_POLY1305;
}

pub fn ring_digests() {
    let _d1 = &SHA256;
    let _d2 = &SHA384;
    let _d3 = &SHA512;
    let _d4 = &SHA1_FOR_LEGACY_USE_ONLY;
}

pub fn ring_asymmetric() {
    let _s1 = &ED25519;
    let _s2 = &RSA_PKCS1_2048_8192_SHA256;
    let _k1 = &X25519;
    let _k2 = &ECDH_P256;
    let _k3 = &ECDH_P384;
}

pub fn rustcrypto_ciphers() {
    let _c1 = Aes256Gcm::new();
    let _c2 = Aes128Gcm::new();
    let _c3 = ChaCha20Poly1305::new();
    let _c4 = Des::new();
    let _c5 = TripleDes::new();
}

pub fn rustcrypto_hashes() {
    let _h1 = Sha256::new();
    let _h2 = Sha384::new();
    let _h3 = Sha512::new();
    let _h4 = Sha3_256::new();
    let _h5 = Sha3_512::new();
    let _h6 = Sha1::new();
    let _h7 = Md5::new();
}

pub fn rustcrypto_keys() {
    let _rsa1 = RsaPrivateKey::new();
    let _rsa2 = RsaPrivateKey::new();
    let _ed1 = SigningKey::generate();
    let _ed2 = SigningKey::generate();
}

pub fn rustcrypto_hmac() {
    type HmacSha256 = Hmac<Sha256>;
    type HmacSha512 = Hmac<Sha512>;
    type HmacSha1 = Hmac<Sha1>;
    type HmacMd5 = Hmac<Md5>;
}

pub fn more_rust_usages() {
    let _x1 = &AES_256_GCM;
    let _x2 = &SHA256;
    let _x3 = &SHA512;
    let _x4 = &ED25519;
    let _x5 = Aes256Gcm::new();
    let _x6 = Sha256::new();
    let _x7 = Sha512::new();
    let _x8 = Sha3_256::new();
    let _x9 = SigningKey::generate();
    let _x10 = RsaPrivateKey::new();
    let _x11 = &X25519;
    let _x12 = &ECDH_P256;
}
