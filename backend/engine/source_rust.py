"""Rust crypto usage detector for ECDAT engine.

Detects cryptographic usages in Rust source files:
- ring (aead, digest, signature, agreement)
- aes-gcm, chacha20poly1305
- sha2, sha3, sha1, md-5
- rsa, ed25519-dalek, p256
- hmac
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_RUST_PATTERNS: list[tuple[re.Pattern[str], Family, CryptoFunction, str, int | None]] = [
    (re.compile(r"\b(?:ring::aead::)?AES_256_GCM\b"), Family.AES, CryptoFunction.ENCRYPT, "ring AES-256-GCM", 256),
    (re.compile(r"\b(?:ring::aead::)?AES_128_GCM\b"), Family.AES, CryptoFunction.ENCRYPT, "ring AES-128-GCM", 128),
    (re.compile(r"\b(?:ring::aead::)?CHACHA20_POLY1305\b"), Family.CHACHA20, CryptoFunction.ENCRYPT, "ring ChaCha20-Poly1305", 256),
    (re.compile(r"\b(?:ring::digest::)?SHA256\b"), Family.SHA_2, CryptoFunction.DIGEST, "ring SHA-256 digest", None),
    (re.compile(r"\b(?:ring::digest::)?SHA384\b"), Family.SHA_2, CryptoFunction.DIGEST, "ring SHA-384 digest", None),
    (re.compile(r"\b(?:ring::digest::)?SHA512\b"), Family.SHA_2, CryptoFunction.DIGEST, "ring SHA-512 digest", None),
    (re.compile(r"\b(?:ring::digest::)?SHA1_FOR_LEGACY_USE_ONLY\b"), Family.SHA_1, CryptoFunction.DIGEST, "ring SHA-1 legacy digest", None),
    (re.compile(r"\b(?:ring::signature::)?ED25519\b"), Family.ED25519, CryptoFunction.SIGN, "ring Ed25519 signature", None),
    (re.compile(r"\b(?:ring::signature::)?RSA_PKCS1_[A-Z0-9_]+\b"), Family.RSA, CryptoFunction.SIGN, "ring RSA-PKCS1 signature", 2048),
    (re.compile(r"\b(?:ring::agreement::)?X25519\b"), Family.X25519, CryptoFunction.KEYDERIVE, "ring X25519 agreement", 256),
    (re.compile(r"\b(?:ring::agreement::)?ECDH_P256\b"), Family.ECDH, CryptoFunction.KEYDERIVE, "ring ECDH-P256 agreement", 256),
    (re.compile(r"\b(?:ring::agreement::)?ECDH_P384\b"), Family.ECDH, CryptoFunction.KEYDERIVE, "ring ECDH-P384 agreement", 384),
    (re.compile(r"\bAes256Gcm(?:::new)?\b"), Family.AES, CryptoFunction.ENCRYPT, "aes-gcm Aes256Gcm", 256),
    (re.compile(r"\bAes128Gcm(?:::new)?\b"), Family.AES, CryptoFunction.ENCRYPT, "aes-gcm Aes128Gcm", 128),
    (re.compile(r"\bChaCha20Poly1305(?:::new)?\b"), Family.CHACHA20, CryptoFunction.ENCRYPT, "chacha20poly1305 ChaCha20Poly1305", 256),
    (re.compile(r"\bSha256(?:::new)?\b"), Family.SHA_2, CryptoFunction.DIGEST, "sha2 Sha256 digest", None),
    (re.compile(r"\bSha384(?:::new)?\b"), Family.SHA_2, CryptoFunction.DIGEST, "sha2 Sha384 digest", None),
    (re.compile(r"\bSha512(?:::new)?\b"), Family.SHA_2, CryptoFunction.DIGEST, "sha2 Sha512 digest", None),
    (re.compile(r"\bSha3_256(?:::new)?\b"), Family.SHA_3, CryptoFunction.DIGEST, "sha3 Sha3_256 digest", None),
    (re.compile(r"\bSha3_512(?:::new)?\b"), Family.SHA_3, CryptoFunction.DIGEST, "sha3 Sha3_512 digest", None),
    (re.compile(r"\bSha1(?:::new)?\b"), Family.SHA_1, CryptoFunction.DIGEST, "sha1 Sha1 digest", None),
    (re.compile(r"\bMd5(?:::new)?\b"), Family.MD5, CryptoFunction.DIGEST, "md5 Md5 digest", None),
    (re.compile(r"\bRsaPrivateKey::new\b"), Family.RSA, CryptoFunction.KEYGEN, "rsa RsaPrivateKey::new", 2048),
    (re.compile(r"\bSigningKey::generate\b"), Family.ED25519, CryptoFunction.KEYGEN, "ed25519-dalek SigningKey::generate", 256),
    (re.compile(r"\bHmac<Sha256>\b"), Family.HMAC, CryptoFunction.TAG, "hmac Hmac<Sha256>", None),
    (re.compile(r"\bHmac<Sha512>\b"), Family.HMAC, CryptoFunction.TAG, "hmac Hmac<Sha512>", None),
    (re.compile(r"\bHmac<Sha1>\b"), Family.HMAC, CryptoFunction.TAG, "hmac Hmac<Sha1>", None),
    (re.compile(r"\bHmac<Md5>\b"), Family.HMAC, CryptoFunction.TAG, "hmac Hmac<Md5>", None),
    (re.compile(r"\bDes(?:::new)?\b"), Family.DES, CryptoFunction.ENCRYPT, "des Des cipher", 56),
    (re.compile(r"\bTripleDes(?:::new)?\b"), Family.THREE_DES, CryptoFunction.ENCRYPT, "des TripleDes cipher", 192),
]


def detect_code(source: bytes, path: str = "<source>", artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    text = source.decode("utf-8", errors="ignore")
    detections: list[Detection] = []

    for pattern, family, fn, display, key_size in _RUST_PATTERNS:
        for match in pattern.finditer(text):
            line = text[: match.start()].count("\n") + 1
            snippet = text[max(0, match.start() - 20) : min(len(text), match.end() + 20)].strip()
            span = Span(
                artifact_hash=artifact_hash,
                kind="ast",
                start=match.start(),
                end=match.end(),
                producing_rule=f"rust_ast.{family.value if family else 'crypto'}",
            )
            detections.append(
                Detection(
                    kind=FindingKind.ALGORITHM if fn != CryptoFunction.TAG else FindingKind.PROTOCOL,
                    surface=Surface.SOURCE,
                    family=family,
                    display_name=display,
                    function=fn,
                    path=path,
                    line=line,
                    symbol=match.group(0),
                    snippet=snippet,
                    source=FindingSource.AST,
                    confidence=0.96,
                    key_size=key_size,
                    spans=[span],
                )
            )

    return detections
