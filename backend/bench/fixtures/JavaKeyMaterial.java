import javax.crypto.spec.SecretKeySpec;
import javax.net.ssl.SSLContext;
import java.security.KeyStore;

public class JavaKeyMaterial {
  public void run(byte[] key) throws Exception {
    SecretKeySpec sks = new SecretKeySpec(key, "AES");
    SSLContext ssl = SSLContext.getInstance("TLSv1.2");
    KeyStore ks = KeyStore.getInstance("PKCS12");
  }
}
