package local.lx04.doubao.screen;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import org.json.JSONObject;

/** Explicit privileged updates; conversation text stays in process memory. */
public final class StateReceiver extends BroadcastReceiver {
    static String state="standby",user="",assistant="";
    static String previousUser="",previousAssistant="",previousStatus="",session="",currentId="";
    static ConversationActivity visible;
    @Override public void onReceive(Context context,Intent intent) {
        String raw=intent.getStringExtra("payload");
        if(raw==null || raw.length()>24000)return;
        try {
            JSONObject data=new JSONObject(raw);
            if(data.optBoolean("reset_history",false)) {
                previousUser="";previousAssistant="";previousStatus="";user="";assistant="";session="";currentId="";
            }
            if(data.optBoolean("reset_current",false)) {
                if(!user.isEmpty()) {
                    previousUser=limit(user,100,false);previousAssistant=limit(assistant,180,true);previousStatus="complete";
                }
                user="";assistant="";currentId="";
            }
            if(data.has("state"))state=data.getString("state");
            if(data.has("user"))user=data.getString("user").substring(0,Math.min(1200,data.getString("user").length()));
            if(data.has("assistant"))assistant=data.getString("assistant").substring(0,Math.min(4000,data.getString("assistant").length()));
            if(data.has("session"))session=data.getString("session");
            JSONObject current=data.optJSONObject("current");
            if(current!=null) {
                currentId=session+":"+current.optString("id");
                user=limit(current.optString("user"),1200,false);
                assistant=limit(current.optString("assistant"),4000,false);
            }
            JSONObject previous=data.optJSONObject("previous");
            if(previous!=null) {
                previousUser=limit(previous.optString("user"),100,false);
                previousAssistant=limit(previous.optString("assistant"),180,true);
                previousStatus=previous.optString("status");
            }
            if(visible!=null)visible.render();
            if(data.optBoolean("show",false))context.startActivity(new Intent(context,ConversationActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP));
        } catch(Exception ignored) { }
    }
    private static String limit(String value,int max,boolean tail) {
        if(value.length()<=max)return value;
        return tail?"…"+value.substring(value.length()-max):value.substring(0,max)+"…";
    }
}
