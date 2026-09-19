import java.security.KeyPairGenerator;
import java.security.spec.ECGenParameterSpec;

public class JavaEcKeygen {
  public void generate() throws Exception {
    KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
    kpg.initialize(new ECGenParameterSpec("secp256r1"));
    KeyPairGenerator kpg2 = KeyPairGenerator.getInstance("EC");
    kpg2.initialize(new ECGenParameterSpec("secp384r1"));
  }
}
