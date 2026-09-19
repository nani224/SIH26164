#include <wolfssl/wolfcrypt/aes.h>
#include <wolfssl/wolfcrypt/rsa.h>
#include <wolfssl/wolfcrypt/hmac.h>

void run(Aes *aes, byte *key, byte *iv, RsaKey *rsakey, WC_RNG *rng,
         Hmac *hmac, byte *hash, byte *data, word32 len, word32 keySz) {
  wc_AesSetKey(aes, key, 32, iv, AES_ENCRYPTION);
  wc_MakeRsaKey(rsakey, 2048, 65537, rng);
  wc_Sha256Hash(data, len, hash);
  wc_HmacSetKey(hmac, WC_SHA256, key, keySz);
}
