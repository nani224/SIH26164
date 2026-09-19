import javax.crypto.Cipher;

public class JavaSafeCipher {
  public void encrypt() throws Exception {
    Cipher aes = Cipher.getInstance("AES/GCM/NoPadding");
    Cipher chacha = Cipher.getInstance("ChaCha20");
  }
}
