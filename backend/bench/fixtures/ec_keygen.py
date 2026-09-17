from cryptography.hazmat.primitives.asymmetric import ec

p256_key = ec.generate_private_key(ec.SECP256R1())
p384_key = ec.generate_private_key(ec.SECP384R1())
