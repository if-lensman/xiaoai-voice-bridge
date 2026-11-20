package local.lx04.doubao.screen;

import android.app.Service;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** Foreground, boot-started local wake recognizer. Cloud connection starts on wake. */
public final class VoiceService extends Service {
    private volatile boolean running;
    private PowerManager.WakeLock wakeLock;
    @Override public void onCreate() {
        super.onCreate();running=true;
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel("voice","豆包本地唤醒",NotificationManager.IMPORTANCE_LOW));
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,ConversationActivity.class),PendingIntent.FLAG_UPDATE_CURRENT);
        startForeground(100,new Notification.Builder(this,"voice").setContentTitle("豆包已就绪")
            .setContentText("本地等待唤醒 · 豆包豆包").setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(open).setOngoing(true).build());
        wakeLock=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"doubao:local-wake");
        wakeLock.acquire();
        new Thread(()->{
            while(running) {
                try {
                    File model=new File(getFilesDir(),"model");model.mkdirs();
                    for(String name:getAssets().list("model")) {
                        File target=new File(model,name);
                        if(target.exists())continue;
                        File temporary=new File(model,name+".tmp");
                        try(InputStream in=getAssets().open("model/"+name);FileOutputStream out=new FileOutputStream(temporary)) {
                            byte[] buffer=new byte[16384];int n;
                            while((n=in.read(buffer))!=-1)out.write(buffer,0,n);
                        }
                        if(!temporary.renameTo(target))throw new IllegalStateException("Model extraction failed");
                    }
                    File config=new File(getFilesDir(),"service-config.json");
                    if(!config.isFile())throw new IllegalStateException("Service config missing");
                    Class.forName("PcmPlayer").getMethod("initialize",android.content.Context.class).invoke(null,this);
                    Class.forName("WakeEndpoint").getMethod("runForever",String.class,String.class)
                        .invoke(null,model.getAbsolutePath(),config.getAbsolutePath());
                } catch(Throwable e) {Log.e("DoubaoService","WORKER_RETRY "+e.getClass().getSimpleName());}
                if(running)try {Thread.sleep(5000);}catch(InterruptedException ignored){}
            }
        },"doubao-local-wake").start();
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {return START_STICKY;}
    @Override public IBinder onBind(Intent intent) {return null;}
    @Override public void onDestroy() {
        running=false;
        try {Class.forName("SessionControl").getField("enabled").setBoolean(null,false);}catch(Exception ignored){}
        if(wakeLock!=null && wakeLock.isHeld())wakeLock.release();
        super.onDestroy();
    }
}
