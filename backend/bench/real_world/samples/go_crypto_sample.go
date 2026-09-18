// Sample from standard Go crypto recipe (BSD-3-Clause)
package main

import (
	"crypto/aes"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
)

func generateKeys() (*rsa.PrivateKey, error) {
	return rsa.GenerateKey(rand.Reader, 2048)
}

func computeHash(data []byte) []byte {
	h := sha256.New()
	h.Write(data)
	return h.Sum(nil)
}

func createCipher(key []byte) error {
	_, err := aes.NewCipher(key)
	return err
}
