#include <openssl/evp.h>

class CipherWrapper {
public:
  void encrypt(EVP_CIPHER_CTX *ctx, unsigned char *key, unsigned char *iv) {
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv);
  }
};
