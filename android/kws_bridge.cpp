#include <jni.h>
#include <string>
#include <vector>
#include "c-api.h"

struct Engine {
  const SherpaOnnxKeywordSpotter *spotter = nullptr;
  const SherpaOnnxOnlineStream *stream = nullptr;
  ~Engine() {
    if (stream) SherpaOnnxDestroyOnlineStream(stream);
    if (spotter) SherpaOnnxDestroyKeywordSpotter(spotter);
  }
};

extern "C" JNIEXPORT jlong JNICALL Java_KwsEngine_create(JNIEnv *env, jclass, jstring directory) {
  const char *path = env->GetStringUTFChars(directory, nullptr);
  std::string base(path);
  env->ReleaseStringUTFChars(directory, path);
  std::string encoder=base+"/encoder-epoch-12-avg-2-chunk-16-left-64.onnx";
  std::string decoder=base+"/decoder-epoch-12-avg-2-chunk-16-left-64.onnx";
  std::string joiner=base+"/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx";
  std::string tokens=base+"/tokens.txt", keywords=base+"/wake.txt";
  SherpaOnnxKeywordSpotterConfig config{};
  config.feat_config.sample_rate=16000; config.feat_config.feature_dim=80;
  config.model_config.transducer={encoder.c_str(),decoder.c_str(),joiner.c_str()};
  config.model_config.tokens=tokens.c_str(); config.model_config.num_threads=2;
  config.model_config.provider="cpu"; config.model_config.model_type="zipformer2";
  config.max_active_paths=8; config.num_trailing_blanks=0;
  config.keywords_score=3.0f; config.keywords_threshold=0.1f;
  config.keywords_file=keywords.c_str();
  Engine *engine=new Engine;
  engine->spotter=SherpaOnnxCreateKeywordSpotter(&config);
  if (engine->spotter) engine->stream=SherpaOnnxCreateKeywordStream(engine->spotter);
  if (!engine->stream) {
    delete engine;
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),"KWS initialization failed");
    return 0;
  }
  return reinterpret_cast<jlong>(engine);
}

extern "C" JNIEXPORT jboolean JNICALL Java_KwsEngine_accept(JNIEnv *env,jclass,jlong handle,jfloatArray samples) {
  Engine *engine=reinterpret_cast<Engine *>(handle);
  jsize count=env->GetArrayLength(samples);
  std::vector<float> pcm(count);
  env->GetFloatArrayRegion(samples,0,count,pcm.data());
  SherpaOnnxOnlineStreamAcceptWaveform(engine->stream,16000,pcm.data(),count);
  bool hit=false;
  while (SherpaOnnxIsKeywordStreamReady(engine->spotter,engine->stream)) {
    SherpaOnnxDecodeKeywordStream(engine->spotter,engine->stream);
    const auto *result=SherpaOnnxGetKeywordResult(engine->spotter,engine->stream);
    if (result && result->keyword && result->keyword[0]) hit=true;
    if (result) SherpaOnnxDestroyKeywordResult(result);
    if (hit) { SherpaOnnxResetKeywordStream(engine->spotter,engine->stream); break; }
  }
  return hit;
}

extern "C" JNIEXPORT void JNICALL Java_KwsEngine_reset(JNIEnv *,jclass,jlong handle) {
  Engine *engine=reinterpret_cast<Engine *>(handle);
  // Recreate stream so feature history from a previous conversation cannot trigger.
  SherpaOnnxDestroyOnlineStream(engine->stream);
  engine->stream=SherpaOnnxCreateKeywordStream(engine->spotter);
}

extern "C" JNIEXPORT void JNICALL Java_KwsEngine_destroy(JNIEnv *,jclass,jlong handle) {
  delete reinterpret_cast<Engine *>(handle);
}
