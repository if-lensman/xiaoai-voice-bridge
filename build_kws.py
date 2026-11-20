"""Compile the small JNI bridge against pinned official sherpa-onnx binaries."""
from pathlib import Path
import hashlib
import os
import json
import shutil
import subprocess
from build_config import ROOT, SDK

MODEL = 'sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile'

def main():
    vendor=ROOT/'vendor'; out=ROOT/'android/build/kws'; out.mkdir(parents=True,exist_ok=True)
    lib=ROOT/'android/build/runtime/install/lib'
    prebuilt=SDK/'ndk'/os.environ.get('NDK_VERSION','28.2.13676358')/'toolchains/llvm/prebuilt'
    toolchain=next(iter(sorted(prebuilt.iterdir())))
    subprocess.run([str(toolchain/'bin/armv7a-linux-androideabi27-clang++'),
        '-std=c++17','-shared','-fPIC','-O2',str(ROOT/'android/kws_bridge.cpp'),
        '-I'+str(vendor),'-L'+str(lib),'-lsherpa-onnx-c-api',
        '-Wl,-rpath,$ORIGIN','-Wl,-z,max-page-size=16384',
        # Android 8 process shutdown must not unload dependency TLS finalizers early.
        '-Wl,-z,nodelete',
        '-o',str(out/'liblx04-kws.so')],check=True)
    shutil.copy2(lib/'libsherpa-onnx-c-api.so',out/'libsherpa-onnx-c-api.so')
    shutil.copy2(vendor/'jniLibs/armeabi-v7a/libonnxruntime.so',out/'libonnxruntime.so')
    shutil.copy2(toolchain/'sysroot/usr/lib/arm-linux-androideabi/libc++_shared.so',out/'libc++_shared.so')
    for path in out.glob('*.so'):
        subprocess.run([str(toolchain/'bin/llvm-strip'),'--strip-unneeded',str(path)],check=True)
    model=out/'model';model.mkdir(exist_ok=True)
    for name in ('encoder-epoch-12-avg-2-chunk-16-left-64.onnx',
                 'decoder-epoch-12-avg-2-chunk-16-left-64.onnx',
                 'joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx','tokens.txt'):
        shutil.copy2(vendor/MODEL/name,model/name)
    (model/'wake.txt').write_text('d òu b āo d òu b āo #0.05 @豆包豆包\n')
    report={'runtime':'k2-fsa/sherpa-onnx v1.13.5','model':MODEL,
            'files':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Built ARMv7 offline KWS bridge and model bundle.')

if __name__=='__main__':main()
