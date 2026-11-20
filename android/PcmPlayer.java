import android.app.Application;
import android.content.Context;
import android.os.Looper;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** Audio API application context used by the foreground voice service. */
public final class PcmPlayer {
    private static boolean initialized;
    static Context appContext;
    public static synchronized void initialize(Context context) {appContext=context.getApplicationContext();initialized=true;}
    public static synchronized void context() throws Exception {
        if(initialized) return;
        if (Looper.myLooper() == null) Looper.prepareMainLooper();
        Class<?> cls = Class.forName("android.app.ActivityThread");
        Object thread = cls.getMethod("systemMain").invoke(null);
        Context context = (Context)cls.getMethod("getSystemContext").invoke(thread);
        Application app = new Application();
        Method attach = Application.class.getDeclaredMethod("attach", Context.class);
        attach.setAccessible(true); attach.invoke(app, context);
        Field initial = cls.getDeclaredField("mInitialApplication");
        initial.setAccessible(true); initial.set(thread, app);
        appContext=context;
        initialized=true;
    }
}
