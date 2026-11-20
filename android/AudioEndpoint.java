import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.AudioManager;
import android.media.MediaRecorder;
import android.os.SystemClock;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.net.InetSocketAddress;
import java.net.InetAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import org.json.JSONObject;

/** Finite manual endpoint over a token-authenticated private LAN connection. */
public final class AudioEndpoint {
    private static final int MAX_FRAME = 262144;
    private static synchronized void send(DataOutputStream out, int kind, byte[] bytes) throws Exception {
        if (bytes.length > MAX_FRAME) throw new IllegalArgumentException("Frame too large");
        out.writeByte(kind); out.writeInt(bytes.length); out.write(bytes); out.flush();
    }
    private static byte[] body(DataInputStream in) throws Exception {
        int length = in.readInt();
        if (length < 0 || length > MAX_FRAME) throw new IllegalArgumentException("Frame too large");
        byte[] bytes = new byte[length]; in.readFully(bytes); return bytes;
    }
    private static JSONObject config(String path) throws Exception {
        File file = new File(path);
        if (file.length() > 4096) throw new IllegalArgumentException("Config too large");
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        try (FileInputStream in = new FileInputStream(file)) {
            byte[] b = new byte[1024]; int count;
            while ((count = in.read(b)) != -1) buffer.write(b, 0, count);
        }
        return new JSONObject(new String(buffer.toByteArray(), StandardCharsets.UTF_8));
    }
    public static void run(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Session config required");
        JSONObject cfg = config(args[0]); int seconds = cfg.getInt("seconds");
        String host = cfg.getString("host");
        if (!host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) throw new IllegalArgumentException("IPv4 address required");
        InetAddress address = InetAddress.getByName(host);
        if ((seconds != 0 && (seconds < 10 || seconds > 120)) || !(address.isSiteLocalAddress() || address.isLoopbackAddress()))
            throw new IllegalArgumentException("Finite private-network session required");
        PcmPlayer.context();
        final Socket socket = new Socket(); socket.setTcpNoDelay(true);
        final DataInputStream in;
        final DataOutputStream out;
        try {
        socket.connect(new InetSocketAddress(cfg.getString("host"), cfg.getInt("port")), 5000);
        socket.setSoTimeout(15000);
        in = new DataInputStream(socket.getInputStream());
        out = new DataOutputStream(socket.getOutputStream());
        JSONObject hello = new JSONObject(); hello.put("version",1); hello.put("rate",16000);
        hello.put("channels",2); hello.put("token",cfg.getString("token"));
        send(out, 0, hello.toString().getBytes(StandardCharsets.UTF_8));
        if (in.readUnsignedByte() != 3 || !"ready".equals(new JSONObject(new String(body(in), StandardCharsets.UTF_8)).getString("type")))
            throw new IllegalStateException("Relay did not become ready");
        } catch(Exception e) {socket.close();throw e;}
        socket.setSoTimeout(seconds==0?45000:(seconds + 20) * 1000);
        int captureMin = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_STEREO, AudioFormat.ENCODING_PCM_16BIT);
        int playMin = AudioTrack.getMinBufferSize(24000, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (captureMin <= 0 || playMin <= 0) throw new IllegalStateException("Audio format unavailable");
        final AudioRecord capture = new AudioRecord(MediaRecorder.AudioSource.MIC,16000,
                AudioFormat.CHANNEL_IN_STEREO,AudioFormat.ENCODING_PCM_16BIT,Math.max(captureMin,32000));
        final AudioTrack playback = new AudioTrack(AudioManager.STREAM_MUSIC,24000,
                AudioFormat.CHANNEL_OUT_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(playMin,9600),AudioTrack.MODE_STREAM);
        final AtomicBoolean running = new AtomicBoolean(true);
        final AtomicBoolean discard = new AtomicBoolean(false);
        final AtomicLong framesWritten = new AtomicLong();
        final Object outputLock=new Object();
        SessionControl.clear();SessionControl.active=true;
        Thread receiver = new Thread(new Runnable() {
            public void run() {
                try {
                    while (running.get()) {
                        int kind = in.readUnsignedByte(); byte[] bytes = body(in);
                        if (kind == 2) {
                            if(discard.get())continue;
                            SessionControl.speaking=true;
                            if (bytes.length % 2 != 0) throw new IllegalStateException("Misaligned output");
                            short[] pcm = new short[bytes.length / 2];
                            for (int i=0;i<pcm.length;i++) {
                                short value = (short)((bytes[2*i]&255) | ((bytes[2*i+1]&255)<<8));
                                pcm[i] = (short)(value * 0.5);
                            }
                            int offset = 0;
                            while (offset < pcm.length && running.get()) {
                                synchronized(outputLock) {
                                    if(discard.get())break;
                                    int n=playback.write(pcm,offset,Math.min(480,pcm.length-offset));
                                    if(n<=0)throw new IllegalStateException("Playback write failed");
                                    offset+=n;framesWritten.addAndGet(n);
                                }
                            }
                        } else if (kind == 5) {
                            if(discard.get())continue;
                            int seq = new JSONObject(new String(bytes,StandardCharsets.UTF_8)).getInt("sequence");
                            long deadline = SystemClock.elapsedRealtime() + 3000;
                            while (running.get() && !discard.get() && (playback.getPlaybackHeadPosition() & 0xffffffffL) < framesWritten.get()
                                    && SystemClock.elapsedRealtime() < deadline) SystemClock.sleep(10);
                            if(discard.get())continue;
                            if ((playback.getPlaybackHeadPosition() & 0xffffffffL) < framesWritten.get())
                                throw new IllegalStateException("Playback did not drain");
                            send(out,6,("{\"sequence\":"+seq+"}").getBytes(StandardCharsets.UTF_8));
                            SessionControl.speaking=false;
                        } else if(kind==8) {
                            discard.set(false);SessionControl.speaking=false;
                        } else if (kind == 9) {
                            running.set(false);
                        } else if (kind == 4) {
                            UiBridge.state("error",false,false);
                            throw new IllegalStateException("Relay reported a session error");
                        } else if (kind == 3) {
                            JSONObject update=new JSONObject(new String(bytes,StandardCharsets.UTF_8));
                            if("ui".equals(update.optString("type"))) {
                                if("speaking".equals(update.optString("state")))SessionControl.speaking=true;
                                UiBridge.update(update);
                            }
                        } else if (kind != 3) {
                            throw new IllegalStateException("Unknown relay frame");
                        }
                    }
                } catch (Exception e) {
                    if (running.get()) System.out.println("OUTPUT_STOP " + e.getClass().getSimpleName());
                    running.set(false);
                }
            }
        });
        receiver.setDaemon(true);
        Thread watchdog = new Thread(new Runnable() {
            public void run() {
                SystemClock.sleep((seconds + 20) * 1000L);
                running.set(false);
                try { socket.close(); } catch (Exception ignored) { }
            }
        }); watchdog.setDaemon(true); if(seconds>0)watchdog.start();
        try {
            if (capture.getState() != AudioRecord.STATE_INITIALIZED || playback.getState() != AudioTrack.STATE_INITIALIZED)
                throw new IllegalStateException("Audio initialization failed");
            playback.play(); capture.startRecording(); receiver.start();
            long deadline = seconds==0?Long.MAX_VALUE:SystemClock.elapsedRealtime() + seconds * 1000L;
            short[] pcm = new short[640];
            double previousInput=0,previousOutput=0,alpha=Math.exp(-2*Math.PI*60/16000);
            long lastInterrupt=0;
            while (running.get() && SessionControl.enabled && SystemClock.elapsedRealtime() < deadline) {
                String command=SessionControl.poll();
                if(command!=null) {
                    synchronized(outputLock) {
                        discard.set(true);playback.pause();playback.flush();framesWritten.set(0);playback.play();
                    }
                    SessionControl.speaking=false;
                    send(out,7,("{\"command\":\""+command+"\"}").getBytes(StandardCharsets.UTF_8));
                    if("end".equals(command)){running.set(false);break;}
                    lastInterrupt=SystemClock.elapsedRealtime();
                }
                int count = capture.read(pcm,0,pcm.length,AudioRecord.READ_NON_BLOCKING);
                if (count < 0) throw new IllegalStateException("Capture read failed: " + count);
                if (count == 0) { SystemClock.sleep(5); continue; }
                if (count % 2 != 0) throw new IllegalStateException("Incomplete stereo frame");
                if(SessionControl.engine!=null && cfg.optBoolean("voice_interrupt",false) && SessionControl.speaking
                    && SystemClock.elapsedRealtime()-lastInterrupt>1500) {
                    float[] mono=new float[count/2];
                    for(int i=0;i<mono.length;i++) {
                        double sample=pcm[2*i],filtered=alpha*(previousOutput+sample-previousInput);
                        previousInput=sample;previousOutput=filtered;
                        mono[i]=(float)(Math.max(-32768,Math.min(32767,filtered*12))/32768.0);
                    }
                    if(SessionControl.engine.feed(mono)) {
                        SessionControl.engine.reset();SessionControl.request("interrupt");
                    }
                }
                byte[] bytes = new byte[count*2];
                for (int i=0;i<count;i++) { bytes[2*i]=(byte)pcm[i]; bytes[2*i+1]=(byte)(pcm[i]>>>8); }
                send(out,1,bytes);
            }
            if(running.get()) send(out,9,new byte[0]);
        } finally {
            running.set(false); socket.close();
            SessionControl.clear();
            if (capture.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) capture.stop();
            capture.release();
            try { playback.stop(); } finally { playback.release(); }
            receiver.join(1000);
        }
    }
}
