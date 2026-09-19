#include "mbedtls/aes.h"
#include "mbedtls/sha256.h"
#include "mbedtls/rsa.h"
#include "mbedtls/ecdsa.h"

void run(mbedtls_aes_context *aes, unsigned char *key,
         mbedtls_sha256_context *sha, mbedtls_rsa_context *rsa,
         mbedtls_ecdsa_context *ecdsa, void *rng) {
  mbedtls_aes_setkey_enc(aes, key, 256);
  mbedtls_sha256_starts(sha);
  mbedtls_rsa_gen_key(rsa, rng, NULL, 3072, 65537);
  mbedtls_ecdsa_genkey(ecdsa, MBEDTLS_ECP_DP_SECP256R1, rng, NULL);
}
