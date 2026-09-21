#include <stdlib.h>
#include <string.h>

void execute_c_crypto_operations(void) {
    // OpenSSL modern fetch API
    EVP_MD_fetch(NULL, "SHA256", NULL);
    EVP_MD_fetch(NULL, "SHA512", NULL);
    EVP_MD_fetch(NULL, "SHA384", NULL);
    EVP_MD_fetch(NULL, "SHA224", NULL);
    EVP_MD_fetch(NULL, "SHA3-256", NULL);
    EVP_MD_fetch(NULL, "SHA3-512", NULL);
    EVP_MD_fetch(NULL, "MD5", NULL);
    EVP_MD_fetch(NULL, "SHA1", NULL);

    EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 2048);
    EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 4096);
    EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_X9_62_prime256v1);

    // OpenSSL pre-3.0 getters
    EVP_sha256();
    EVP_sha512();
    EVP_sha384();
    EVP_sha224();
    EVP_sha3_256();
    EVP_sha3_512();
    EVP_md5();
    EVP_sha1();

    // mbedTLS
    mbedtls_aes_setkey_enc(ctx, key, 256);
    mbedtls_aes_setkey_dec(ctx, key, 128);
    mbedtls_des_setkey_enc(ctx, key);
    mbedtls_des_setkey_dec(ctx, key);
    mbedtls_des3_set2key_enc(ctx, key);
    mbedtls_des3_set3key_enc(ctx, key);
    mbedtls_sha256_starts(ctx, 0);
    mbedtls_sha1_starts(ctx);
    mbedtls_md5_starts(ctx);
    mbedtls_rsa_gen_key(ctx, f_rng, p_rng, 2048, 65537);
    mbedtls_ecdsa_genkey(ctx, MBEDTLS_ECP_DP_SECP256R1, f_rng, p_rng);
    mbedtls_gcm_setkey(ctx, MBEDTLS_CIPHER_ID_AES, key, 256);

    // wolfSSL
    wc_AesSetKey(aes, key, 32, iv, AES_ENCRYPTION);
    wc_Des3_SetKey(des3, key, iv, DES_ENCRYPTION);
    wc_MakeRsaKey(key, 2048, 65537, rng);
    wc_ecc_make_key(rng, 32, key);
    wc_Sha256Hash(data, len, hash);
    wc_ShaHash(data, len, hash);
    wc_Md5Hash(data, len, hash);
    wc_HmacSetKey(hmac, WC_SHA256, key, keySz);
}
