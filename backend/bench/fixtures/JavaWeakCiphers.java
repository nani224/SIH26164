import javax.crypto.Cipher;

public class JavaWeakCiphers {
  public void encrypt() throws Exception {
    Cipher des = Cipher.getInstance("DES/ECB/PKCS5Padding");
    Cipher tdes = Cipher.getInstance("DESede/CBC/PKCS5Padding");
    Cipher blowfish = Cipher.getInstance("Blowfish/ECB/PKCS5Padding");
  }
}
