from cryptography.hazmat.primitives.asymmetric import rsa

small_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
large_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
