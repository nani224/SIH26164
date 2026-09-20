import javax.crypto.SecretKeyFactory;

public class JavaSecretKeyFactory {
  public void derive() throws Exception {
    SecretKeyFactory f256 = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
    SecretKeyFactory f1 = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
  }
}
