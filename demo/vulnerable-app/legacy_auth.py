"""Legacy auth token signing -- generates a fresh RSA keypair per process
start and signs session tokens with it.

DELIBERATELY VULNERABLE (demo): 1024-bit RSA is far below the 2048-bit
minimum any current guidance recommends, and is the kind of change
ECDAT's `.ecdat-policy.yml` gate (failOnBand: critical) is built to catch
before it merges -- see nani224/SIH26164's M5 (Track CC) CI/CD work.
"""

from cryptography.hazmat.primitives.asymmetric import rsa


def generate_signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=1024)


def sign_session_token(key: rsa.RSAPrivateKey, token_bytes: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    return key.sign(token_bytes, padding.PKCS1v15(), hashes.SHA256())
