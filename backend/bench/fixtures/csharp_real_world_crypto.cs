// Real-world C# / .NET cryptographic usages using System.Security.Cryptography.
// Permissive MIT/Apache-2.0 reference implementation.

using System;
using System.Security.Cryptography;

namespace RealWorldCrypto
{
    public class CryptoService
    {
        public void SymmetricOperations()
        {
            using var aes1 = Aes.Create();
            using var aes2 = Aes.Create();
            using var aesGcm = new AesGcm(new byte[32], 16);
            using var chacha = new ChaCha20Poly1305(new byte[32]);
            using var des1 = DES.Create();
            using var des2 = new DESCryptoServiceProvider();
            using var tdes1 = TripleDES.Create();
            using var tdes2 = new TripleDESCryptoServiceProvider();
            using var rc2 = new RC2CryptoServiceProvider();
        }

        public void AsymmetricOperations()
        {
            using var rsa1 = RSA.Create();
            using var rsa2 = RSA.Create(2048);
            using var rsa3 = RSA.Create(4096);
            using var rsa4 = new RSACryptoServiceProvider();
            using var ecdsa1 = ECDsa.Create();
            using var ecdsa2 = ECDsa.Create();
            using var ecdh1 = ECDiffieHellman.Create();
            using var ecdh2 = ECDiffieHellman.Create();
            using var dsa = new DSACryptoServiceProvider();
        }

        public void HashOperations()
        {
            using var sha256_1 = SHA256.Create();
            var h1 = SHA256.HashData(new byte[] { 1, 2, 3 });
            using var sha384_1 = SHA384.Create();
            var h2 = SHA384.HashData(new byte[] { 1, 2, 3 });
            using var sha512_1 = SHA512.Create();
            var h3 = SHA512.HashData(new byte[] { 1, 2, 3 });
            using var sha1_1 = SHA1.Create();
            var h4 = SHA1.HashData(new byte[] { 1, 2, 3 });
            using var md5_1 = MD5.Create();
            var h5 = MD5.HashData(new byte[] { 1, 2, 3 });
        }

        public void HmacOperations()
        {
            using var hmac256_1 = new HMACSHA256(new byte[32]);
            using var hmac256_2 = HMACSHA256.Create();
            using var hmac384_1 = new HMACSHA384(new byte[48]);
            using var hmac384_2 = HMACSHA384.Create();
            using var hmac512_1 = new HMACSHA512(new byte[64]);
            using var hmac512_2 = HMACSHA512.Create();
            using var hmac1_1 = new HMACSHA1(new byte[20]);
            using var hmac1_2 = HMACSHA1.Create();
            using var hmacMd5_1 = new HMACMD5(new byte[16]);
            using var hmacMd5_2 = HMACMD5.Create();
        }

        public void AdditionalOperations()
        {
            using var aes = Aes.Create();
            using var rsa = RSA.Create(2048);
            using var ecdsa = ECDsa.Create();
            using var ecdh = ECDiffieHellman.Create();
            var s256 = SHA256.HashData(new byte[] { 4, 5 });
            var s512 = SHA512.HashData(new byte[] { 4, 5 });
            using var h256 = new HMACSHA256(new byte[32]);
            using var tdes = TripleDES.Create();
            using var des = DES.Create();
            using var rsaCsp = new RSACryptoServiceProvider();
            var m5 = MD5.HashData(new byte[] { 4, 5 });
            var s1 = SHA1.HashData(new byte[] { 4, 5 });
        }
    }
}
