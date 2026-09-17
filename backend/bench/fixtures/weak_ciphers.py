from cryptography.hazmat.primitives.ciphers import algorithms

triple_des = algorithms.TripleDES(key)
rc4 = algorithms.ARC4(key)
blowfish = algorithms.Blowfish(key)
