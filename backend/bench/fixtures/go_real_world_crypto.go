package main

import (
	"crypto/aes"
	"crypto/des"
	"crypto/dsa"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/elliptic"
	"crypto/hmac"
	"crypto/md5"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"golang.org/x/crypto/sha3"
)

func hashOperations() {
	_ = md5.New()
	_ = md5.Sum([]byte("data"))
	_ = sha1.New()
	_ = sha1.Sum([]byte("data"))
	_ = sha256.New()
	_ = sha256.Sum256([]byte("data"))
	_ = sha256.Sum224([]byte("data"))
	_ = sha512.New()
	_ = sha512.Sum512([]byte("data"))
	_ = sha512.Sum384([]byte("data"))
	_ = sha512.Sum512_224([]byte("data"))
	_ = sha512.Sum512_256([]byte("data"))
	_ = sha3.New256()
	_ = sha3.New512()
}

func rsaOperations() {
	key, _ := rsa.GenerateKey(rand.Reader, 2048)
	key2, _ := rsa.GenerateKey(rand.Reader, 4096)
	hashed := sha256.Sum256([]byte("msg"))
	sig1, _ := rsa.SignPKCS1v15(rand.Reader, key, 0, hashed[:])
	_ = rsa.VerifyPKCS1v15(&key.PublicKey, 0, hashed[:], sig1)
	sig2, _ := rsa.SignPSS(rand.Reader, key, 0, hashed[:], nil)
	_ = rsa.VerifyPSS(&key.PublicKey, 0, hashed[:], sig2, nil)
	enc, _ := rsa.EncryptOAEP(sha256.New(), rand.Reader, &key.PublicKey, []byte("secret"), nil)
	_, _ = rsa.DecryptOAEP(sha256.New(), rand.Reader, key, enc, nil)
	enc2, _ := rsa.EncryptPKCS1v15(rand.Reader, &key.PublicKey, []byte("secret"))
	_, _ = rsa.DecryptPKCS1v15(rand.Reader, key, enc2)
	_ = key2
}

func ecdsaOperations() {
	ecKey, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	ecKey2, _ := ecdsa.GenerateKey(elliptic.P384(), rand.Reader)
	digest := sha256.Sum256([]byte("msg"))
	r, s, _ := ecdsa.Sign(rand.Reader, ecKey, digest[:])
	_ = ecdsa.Verify(&ecKey.PublicKey, digest[:], r, s)
	asnSig, _ := ecdsa.SignASN1(rand.Reader, ecKey, digest[:])
	_ = ecdsa.VerifyASN1(&ecKey.PublicKey, digest[:], asnSig)
	_ = ecKey2
}

func ed25519Operations() {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	sig := ed25519.Sign(priv, []byte("message"))
	_ = ed25519.Verify(pub, []byte("message"), sig)
}

func dsaOperations() {
	var params dsa.Parameters
	_ = dsa.Sign(rand.Reader, nil, []byte("hash"))
	_ = dsa.Verify(nil, []byte("hash"), nil, nil)
	_ = params
}

func cipherOperations() {
	_, _ = aes.NewCipher([]byte("1234567890123456"))
	_, _ = aes.NewCipher([]byte("12345678901234567890123456789012"))
	_, _ = des.NewCipher([]byte("12345678"))
	_, _ = des.NewTripleDESCipher([]byte("123456789012345678901234"))
}

func hmacOperations() {
	_ = hmac.New(sha256.New, []byte("key1"))
	_ = hmac.New(sha512.New, []byte("key2"))
	_ = hmac.New(sha1.New, []byte("key3"))
	_ = hmac.New(md5.New, []byte("key4"))
}
