import java.util.concurrent.atomic.AtomicReference;

/** Process-local controls shared by the Android service and screen. */
public final class SessionControl {
    private static final AtomicReference<String> pending=new AtomicReference<String>();
    public static volatile boolean enabled=true, active=false, speaking=false;
    static KwsEngine engine;
    public static void request(String command) {
        if((active && ("interrupt".equals(command)||"end".equals(command))) || (!active && "wake".equals(command)))pending.set(command);
    }
    static String poll() {return pending.getAndSet(null);}
    static void clear() {pending.set(null);active=false;speaking=false;}
}
