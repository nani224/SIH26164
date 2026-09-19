import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.engines.AESEngine;
import org.bouncycastle.crypto.generators.RSAKeyPairGenerator;
import org.bouncycastle.crypto.generators.Ed25519KeyPairGenerator;

public class JavaBouncyCastle {
  public void run() {
    SHA256Digest digest = new SHA256Digest();
    AESEngine cipher = new AESEngine();
    RSAKeyPairGenerator rsaGen = new RSAKeyPairGenerator();
    Ed25519KeyPairGenerator edGen = new Ed25519KeyPairGenerator();
  }
}
