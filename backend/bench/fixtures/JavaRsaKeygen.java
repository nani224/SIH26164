import java.security.KeyPairGenerator;

public class JavaRsaKeygen {
  public void generate() throws Exception {
    KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
    kpg.initialize(2048);
    KeyPairGenerator kpg2 = KeyPairGenerator.getInstance("RSA");
    kpg2.initialize(4096);
  }
}
