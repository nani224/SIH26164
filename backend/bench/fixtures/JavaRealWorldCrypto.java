package com.example.crypto;

import java.security.*;
import javax.crypto.*;
import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.engines.AESEngine;
import org.bouncycastle.crypto.engines.RSAEngine;
import org.bouncycastle.crypto.generators.Ed25519KeyPairGenerator;

public class JavaRealWorldCrypto {
    public void executeCryptoOperations() throws Exception {
        MessageDigest d1 = MessageDigest.getInstance("SHA-256");
        MessageDigest d2 = MessageDigest.getInstance("SHA-512");
        MessageDigest d3 = MessageDigest.getInstance("SHA-384");
        MessageDigest d4 = MessageDigest.getInstance("MD5");
        MessageDigest d5 = MessageDigest.getInstance("SHA-1");
        MessageDigest d6 = MessageDigest.getInstance("SHA3-256");
        MessageDigest d7 = MessageDigest.getInstance("SHA3-512");

        Cipher c1 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        Cipher c2 = Cipher.getInstance("AES/GCM/NoPadding");
        Cipher c3 = Cipher.getInstance("DES/ECB/PKCS5Padding");
        Cipher c4 = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        Cipher c5 = Cipher.getInstance("Blowfish/CBC/PKCS5Padding");
        Cipher c6 = Cipher.getInstance("RC4");
        Cipher c7 = Cipher.getInstance("ChaCha20");
        Cipher c8 = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");

        KeyPairGenerator kpg1 = KeyPairGenerator.getInstance("RSA");
        KeyPairGenerator kpg2 = KeyPairGenerator.getInstance("EC");
        KeyPairGenerator kpg3 = KeyPairGenerator.getInstance("DSA");

        KeyGenerator kg1 = KeyGenerator.getInstance("AES");
        KeyGenerator kg2 = KeyGenerator.getInstance("HmacSHA256");
        KeyGenerator kg3 = KeyGenerator.getInstance("DESede");

        Signature s1 = Signature.getInstance("SHA256withRSA");
        Signature s2 = Signature.getInstance("SHA512withRSA");
        Signature s3 = Signature.getInstance("SHA256withECDSA");
        Signature s4 = Signature.getInstance("Ed25519");
        Signature s5 = Signature.getInstance("SHA1withDSA");

        KeyAgreement ka1 = KeyAgreement.getInstance("ECDH");
        KeyAgreement ka2 = KeyAgreement.getInstance("X25519");
        KeyAgreement ka3 = KeyAgreement.getInstance("DH");

        Mac m1 = Mac.getInstance("HmacSHA256");
        Mac m2 = Mac.getInstance("HmacSHA512");
        Mac m3 = Mac.getInstance("HmacSHA1");
        Mac m4 = Mac.getInstance("HmacMD5");

        SecretKeyFactory skf1 = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        SecretKeyFactory skf2 = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA512");

        SHA256Digest bcDigest = new SHA256Digest();
        AESEngine bcAes = new AESEngine();
        RSAEngine bcRsa = new RSAEngine();
        Ed25519KeyPairGenerator bcEd = new Ed25519KeyPairGenerator();
    }
}
