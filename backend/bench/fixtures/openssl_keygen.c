#include <openssl/evp.h>

void run(EVP_PKEY_CTX *ctx) {
  EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 2048);
  EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_X9_62_prime256v1);
}
