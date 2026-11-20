import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.SystemClock;

/** Foreground-service local wake -> conversation -> standby loop. */
public final class WakeEndpoint {
    private static boolean waitForWake(KwsEngine engine,long deadline) throws Exception {
        int min=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_STEREO,AudioFormat.ENCODING_PCM_16BIT);
        AudioRecord capture=new AudioRecord(MediaRecorder.AudioSource.MIC,16000,
            AudioFormat.CHANNEL_IN_STEREO,AudioFormat.ENCODING_PCM_16BIT,Math.max(min,32000));
        double previousInput=0,previousOutput=0,alpha=Math.exp(-2*Math.PI*60/16000);
        try {
            if(capture.getState()!=AudioRecord.STATE_INITIALIZED) throw new IllegalStateException("Standby microphone unavailable");
            capture.startRecording();
            UiBridge.state("standby",false,false);
            short[] stereo=new short[640];
            while(SessionControl.enabled && SystemClock.elapsedRealtime()<deadline) {
                if("wake".equals(SessionControl.poll())) {
                    UiBridge.state("connecting",true,true);return true;
                }
                int count=capture.read(stereo,0,stereo.length,AudioRecord.READ_NON_BLOCKING);
                if(count<0 || count%2!=0) throw new IllegalStateException("Standby capture failed");
                if(count==0) { SystemClock.sleep(5);continue; }
                float[] mono=new float[count/2];
                for(int i=0;i<mono.length;i++) {
                    double sample=stereo[2*i];
                    double filtered=alpha*(previousOutput+sample-previousInput);
                    previousInput=sample;previousOutput=filtered;
                    mono[i]=(float)(Math.max(-32768,Math.min(32767,filtered*12))/32768.0);
                }
                boolean detected=engine.feed(mono);
                if(detected) {
                    UiBridge.state("connecting",true,true);return true;
                }
            }
            return false;
        } finally {
            if(capture.getRecordingState()==AudioRecord.RECORDSTATE_RECORDING)capture.stop();
            capture.release();
        }
    }
    public static void runForever(String model,String config) throws Exception {
        PcmPlayer.context();SessionControl.enabled=true;
        UiBridge.state("standby",false,true);
        try(KwsEngine engine=new KwsEngine(model)) {
            SessionControl.engine=engine;
            while(SessionControl.enabled) {
                engine.reset();
                if(!waitForWake(engine,Long.MAX_VALUE))break;
                try {AudioEndpoint.run(new String[]{config});}
                catch(Exception e) {System.out.println("SESSION_FAILED "+e.getClass().getSimpleName());UiBridge.state("error",false,false);}
                SessionControl.clear();SystemClock.sleep(500);
            }
        } finally {SessionControl.engine=null;}
    }
}
