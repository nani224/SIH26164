"""Real-world Python cryptographic usages based on standard library and cryptography hazmat.
Permissive Apache-2.0 / MIT style reference code.
"""

import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def hashes_demo():
    h1 = hashlib.md5(b"test").hexdigest()
    h2 = hashlib.sha1(b"test").hexdigest()
    h3 = hashlib.sha224(b"test").hexdigest()
    h4 = hashlib.sha256(b"test").hexdigest()
    h5 = hashlib.sha384(b"test").hexdigest()
    h6 = hashlib.sha512(b"test").hexdigest()
    h7 = hashlib.sha3_224(b"test").hexdigest()
    h8 = hashlib.sha3_256(b"test").hexdigest()
    h9 = hashlib.sha3_384(b"test").hexdigest()
    h10 = hashlib.sha3_512(b"test").hexdigest()
    return [h1, h2, h3, h4, h5, h6, h7, h8, h9, h10]


def hmac_demo():
    mac1 = hmac.new(b"key1", b"msg", hashlib.sha256).digest()
    mac2 = hmac.new(b"key2", b"msg", hashlib.sha512).digest()
    mac3 = hmac.new(b"key3", b"msg", hashlib.sha1).digest()
    mac4 = hmac.new(b"key4", b"msg", hashlib.md5).digest()
    return [mac1, mac2, mac3, mac4]


def keygen_demo():
    rsa_key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_key2 = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    rsa_key3 = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    ec_key1 = ec.generate_private_key(ec.SECP256R1())
    ec_key2 = ec.generate_private_key(ec.SECP384R1())
    ec_key3 = ec.generate_private_key(ec.SECP521R1())
    ed_key1 = ed25519.Ed25519PrivateKey.generate()
    ed_key2 = ed25519.Ed25519PrivateKey.generate()
    return [rsa_key1, rsa_key2, rsa_key3, ec_key1, ec_key2, ec_key3, ed_key1, ed_key2]


def cipher_demo():
    c1 = Cipher(algorithms.AES(b"0" * 32), modes.CBC(b"0" * 16))
    c2 = Cipher(algorithms.AES(b"0" * 16), modes.CBC(b"0" * 16))
    c3 = Cipher(algorithms.TripleDES(b"0" * 24), modes.CBC(b"0" * 8))
    c4 = Cipher(algorithms.ChaCha20(b"0" * 32, b"0" * 16), mode=None)
    c5 = Cipher(algorithms.ARC4(b"0" * 16), mode=None)
    c6 = Cipher(algorithms.Blowfish(b"0" * 16), modes.CBC(b"0" * 8))
    c7 = Cipher(algorithms.AES(b"1" * 32), modes.GCM(b"1" * 12))
    c8 = Cipher(algorithms.TripleDES(b"1" * 16), modes.CBC(b"1" * 8))
    return [c1, c2, c3, c4, c5, c6, c7, c8]


def more_hashes():
    a = hashlib.sha256(b"salt1").digest()
    b = hashlib.sha512(b"salt2").digest()
    c = hashlib.sha384(b"salt3").digest()
    d = hashlib.md5(b"salt4").digest()
    e = hashlib.sha1(b"salt5").digest()
    return [a, b, c, d, e]


def more_keys():
    k1 = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    k2 = ec.generate_private_key(ec.SECP256K1())
    k3 = ed25519.Ed25519PrivateKey.generate()
    return [k1, k2, k3]
