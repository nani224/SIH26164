import java.util.ArrayList;
import java.util.HashMap;

public class JavaNoCrypto {
  public void run() {
    StringBuilder sb = new StringBuilder();
    ArrayList<String> list = new ArrayList<>();
    HashMap<String, String> map = new HashMap<>();
    sb.append("hello").append(list.size()).append(map.size());
  }
}
