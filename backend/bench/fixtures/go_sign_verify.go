package fixtures

import (
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/rsa"
)

func run() {
	_ = rsa.SignPKCS1v15(nil, nil, 0, nil)
	_ = rsa.VerifyPKCS1v15(nil, 0, nil, nil)
	_, _ = ecdsa.Sign(nil, nil, nil)
	_ = ecdsa.Verify(nil, nil, nil, nil)
	_ = ed25519.Sign(nil, nil)
	_ = ed25519.Verify(nil, nil, nil)
}
