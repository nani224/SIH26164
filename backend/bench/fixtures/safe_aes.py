from cryptography.hazmat.primitives.ciphers import algorithms

cipher = algorithms.AES(key256)
stream = algorithms.ChaCha20(key256, nonce)
