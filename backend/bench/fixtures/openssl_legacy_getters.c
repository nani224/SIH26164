#include <openssl/evp.h>

void run(EVP_CIPHER_CTX *ctx, unsigned char *key, unsigned char *iv) {
  EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, key, iv);
  EVP_EncryptInit_ex(ctx, EVP_des_ede3_cbc(), NULL, key, iv);
  EVP_DigestInit_ex(ctx, EVP_sha1(), NULL);
}
