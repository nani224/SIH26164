import javax.crypto.Mac;

public class JavaHmac {
  public void tag() throws Exception {
    Mac hmac256 = Mac.getInstance("HmacSHA256");
    Mac hmac1 = Mac.getInstance("HmacSHA1");
  }
}
