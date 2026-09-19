import java.security.Signature;
import javax.crypto.KeyAgreement;

public class JavaSignatureKeyAgreement {
  public void run() throws Exception {
    Signature rsaSig = Signature.getInstance("SHA256withRSA");
    Signature ecSig = Signature.getInstance("SHA256withECDSA");
    KeyAgreement ka = KeyAgreement.getInstance("ECDH");
  }
}
