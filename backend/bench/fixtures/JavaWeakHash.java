import java.security.MessageDigest;

public class JavaWeakHash {
  public void hash() throws Exception {
    MessageDigest md5a = MessageDigest.getInstance("MD5");
    MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
    MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
    MessageDigest md5b = MessageDigest.getInstance("MD5");
  }
}
