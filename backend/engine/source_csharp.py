"""C# / .NET crypto usage detector for ECDAT engine.

Detects cryptographic usages in C# (.cs) source files:
- System.Security.Cryptography (Aes, RSA, ECDsa, SHA256, HMACSHA256, DES, TripleDES)
"""

from __future__ import annotations

import contextlib
import hashlib
import re

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_CSHARP_PATTERNS: list[tuple[re.Pattern[str], Family, CryptoFunction, str, int | None]] = [
    (re.compile(r"\bAes\.Create\(\)"), Family.AES, CryptoFunction.ENCRYPT, "Aes.Create()", 256),
    (re.compile(r"\b(?:new\s+)?AesGcm\s*\("), Family.AES, CryptoFunction.ENCRYPT, "AesGcm", 256),
    (
        re.compile(r"\b(?:new\s+)?ChaCha20Poly1305\s*\("),
        Family.CHACHA20,
        CryptoFunction.ENCRYPT,
        "ChaCha20Poly1305",
        256,
    ),
    (re.compile(r"\bRSA\.Create\((?:(\d+))?\)"), Family.RSA, CryptoFunction.KEYGEN, "RSA.Create()", 2048),
    (re.compile(r"\bRSACryptoServiceProvider\b"), Family.RSA, CryptoFunction.KEYGEN, "RSACryptoServiceProvider", 2048),
    (re.compile(r"\bECDsa\.Create\(\)"), Family.ECDSA, CryptoFunction.KEYGEN, "ECDsa.Create()", 256),
    (
        re.compile(r"\bECDiffieHellman\.Create\(\)"),
        Family.ECDH,
        CryptoFunction.KEYDERIVE,
        "ECDiffieHellman.Create()",
        256,
    ),
    (re.compile(r"\bDSACryptoServiceProvider\b"), Family.DSA, CryptoFunction.SIGN, "DSACryptoServiceProvider", 1024),
    (re.compile(r"\bSHA256\.(?:Create\(\)|HashData\b)"), Family.SHA_2, CryptoFunction.DIGEST, "SHA256", None),
    (re.compile(r"\bSHA384\.(?:Create\(\)|HashData\b)"), Family.SHA_2, CryptoFunction.DIGEST, "SHA384", None),
    (re.compile(r"\bSHA512\.(?:Create\(\)|HashData\b)"), Family.SHA_2, CryptoFunction.DIGEST, "SHA512", None),
    (re.compile(r"\bSHA1\.(?:Create\(\)|HashData\b)"), Family.SHA_1, CryptoFunction.DIGEST, "SHA1", None),
    (re.compile(r"\bMD5\.(?:Create\(\)|HashData\b)"), Family.MD5, CryptoFunction.DIGEST, "MD5", None),
    (re.compile(r"\b(?:new\s+)?HMACSHA256\s*(?:\(|\.Create\b)"), Family.HMAC, CryptoFunction.TAG, "HMACSHA256", None),
    (re.compile(r"\b(?:new\s+)?HMACSHA384\s*(?:\(|\.Create\b)"), Family.HMAC, CryptoFunction.TAG, "HMACSHA384", None),
    (re.compile(r"\b(?:new\s+)?HMACSHA512\s*(?:\(|\.Create\b)"), Family.HMAC, CryptoFunction.TAG, "HMACSHA512", None),
    (re.compile(r"\b(?:new\s+)?HMACSHA1\s*(?:\(|\.Create\b)"), Family.HMAC, CryptoFunction.TAG, "HMACSHA1", None),
    (re.compile(r"\b(?:new\s+)?HMACMD5\s*(?:\(|\.Create\b)"), Family.HMAC, CryptoFunction.TAG, "HMACMD5", None),
    (
        re.compile(r"\b(?:TripleDESCryptoServiceProvider\b|TripleDES\.Create\(\))"),
        Family.THREE_DES,
        CryptoFunction.ENCRYPT,
        "TripleDES",
        192,
    ),
    (re.compile(r"\b(?:DESCryptoServiceProvider\b|DES\.Create\(\))"), Family.DES, CryptoFunction.ENCRYPT, "DES", 56),
    (re.compile(r"\bRC2CryptoServiceProvider\b"), Family.RC4, CryptoFunction.ENCRYPT, "RC2", 128),
]


def detect_code(source: bytes, path: str = "<source>", artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()

    text = source.decode("utf-8", errors="ignore")
    detections: list[Detection] = []

    for pattern, family, fn, display, default_key_size in _CSHARP_PATTERNS:
        for match in pattern.finditer(text):
            line = text[: match.start()].count("\n") + 1
            snippet = text[max(0, match.start() - 20) : min(len(text), match.end() + 20)].strip()
            key_size = default_key_size
            if match.groups() and match.group(1):
                with contextlib.suppress(ValueError):
                    key_size = int(match.group(1))

            span = Span(
                artifact_hash=artifact_hash,
                kind="ast",
                start=match.start(),
                end=match.end(),
                producing_rule=f"csharp_ast.{family.value if family else 'crypto'}",
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
