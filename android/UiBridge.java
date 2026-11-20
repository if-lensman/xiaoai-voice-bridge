import android.content.Intent;
import android.content.ComponentName;
import org.json.JSONObject;

/** Display updates contain text/status only, never cloud credentials. */
public final class UiBridge {
    static void update(JSONObject payload) {
        if(PcmPlayer.appContext==null)return;
        try {
            Intent intent=new Intent("local.lx04.doubao.SCREEN_STATE");
            intent.setComponent(new ComponentName("local.lx04.doubao.screen","local.lx04.doubao.screen.StateReceiver"));
            intent.putExtra("payload",payload.toString());
            PcmPlayer.appContext.sendBroadcast(intent);
        } catch(Exception e) {System.out.println("SCREEN_UPDATE_FAILED "+e.getClass().getSimpleName());}
    }
    static void state(String state,boolean show,boolean clear) {
        try {
            JSONObject payload=new JSONObject().put("state",state).put("show",show);
            if(clear)payload.put("reset_current",true).put("user","").put("assistant","");
            update(payload);
        } catch(Exception ignored) { }
    }
}
