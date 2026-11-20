/** Device-local keyword recognition. No sockets or microphone files. */
public final class KwsEngine implements AutoCloseable {
    static { System.loadLibrary("lx04-kws"); }
    private long handle;
    private static native long create(String directory);
    private static native boolean accept(long handle,float[] samples);
    private static native void reset(long handle);
    private static native void destroy(long handle);
    public KwsEngine(String directory) { handle=create(directory); }
    public boolean feed(float[] samples) {
        if (handle==0) throw new IllegalStateException("Closed KWS");
        return accept(handle,samples);
    }
    public void reset() { if (handle!=0) reset(handle); }
    public void close() { if (handle!=0) { destroy(handle); handle=0; } }
}
