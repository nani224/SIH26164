#include <openssl/evp.h>

void run(void) {
  EVP_CIPHER *cipher = EVP_CIPHER_fetch(NULL, "AES-256-GCM", NULL);
  EVP_MD *md = EVP_MD_fetch(NULL, "SHA256", NULL);
}
