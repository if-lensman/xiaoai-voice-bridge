"""Build sherpa-onnx without unused TTS/espeak components for the release APK."""
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request
import zipfile
from build_config import ROOT, SDK

SOURCE_SHA256='99f520db7364a06be0c174a385d03f9ccdbfe08f61146055229e4a990e285262'
# ORT headers match the pinned Android runtime bundled by sherpa-onnx v1.13.5.
ORT_VERSION='1.27.1'

def main():
    vendor=ROOT/'vendor';vendor.mkdir(exist_ok=True)
    source_archive=vendor/'sherpa-onnx-v1.13.5-source.tar.gz'
    if not source_archive.exists():
        urllib.request.urlretrieve('https://codeload.github.com/k2-fsa/sherpa-onnx/tar.gz/refs/tags/v1.13.5',source_archive)
    if hashlib.sha256(source_archive.read_bytes()).hexdigest()!=SOURCE_SHA256:
        raise RuntimeError('sherpa source checksum mismatch')
    with tarfile.open(source_archive) as tar:
        tar.extractall(vendor,members=[m for m in tar.getmembers() if m.isfile() or m.isdir()],filter='data')
    ort_archive=vendor/'onnxruntime-android-1.27.1.zip'
    subprocess.run(['gh','release','download','v1.27.1','--repo','csukuangfj/onnxruntime-libs',
                    '--pattern',ort_archive.name,'--dir',str(vendor),'--skip-existing'],check=True)
    if hashlib.sha256(ort_archive.read_bytes()).hexdigest()!='defade26209f72cf4fa9769b18052c842833d6bef12924595d26f03b995548ca':
        raise RuntimeError('ORT archive checksum mismatch')
    headers=vendor/'ort/headers'
    with zipfile.ZipFile(ort_archive) as archive:
        for name in archive.namelist():
            if name.startswith('headers/') and not name.endswith('/'):
                target=vendor/'ort'/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.read(name))
    out=ROOT/'android/build/runtime';ndk=SDK/'ndk'/os.environ.get('NDK_VERSION','28.2.13676358')
    env=os.environ.copy();env['GIT_CEILING_DIRECTORIES']=str(vendor)
    env['SHERPA_ONNXRUNTIME_INCLUDE_DIR']=str(headers)
    env['SHERPA_ONNXRUNTIME_LIB_DIR']=str(vendor/'jniLibs/armeabi-v7a')
    args=['cmake','-S',str(vendor/'sherpa-onnx-1.13.5'),'-B',str(out),'-G','Ninja',
          '-DCMAKE_TOOLCHAIN_FILE='+str(ndk/'build/cmake/android.toolchain.cmake'),
          '-DANDROID_ABI=armeabi-v7a','-DANDROID_PLATFORM=android-27','-DCMAKE_SYSTEM_VERSION=27','-DCMAKE_BUILD_TYPE=Release',
          '-DCMAKE_C_FLAGS=-ffile-prefix-map='+str(ROOT)+'=/src',
          '-DCMAKE_CXX_FLAGS=-ffile-prefix-map='+str(ROOT)+'=/src',
          '-DCMAKE_INSTALL_PREFIX='+str(out/'install'),'-DBUILD_SHARED_LIBS=ON',
          '-DSHERPA_ONNX_ENABLE_C_API=ON']
    for option in ('TTS','SPEAKER_DIARIZATION','PYTHON','TESTS','CHECK','PORTAUDIO','JNI','WEBSOCKET','BINARY'):
        args.append('-DSHERPA_ONNX_ENABLE_'+option+'=OFF')
    subprocess.run(args,env=env,check=True)
    subprocess.run(['cmake','--build',str(out),'--target','install','-j',os.environ.get('BUILD_JOBS','4')],env=env,check=True)
    print('Built ARMv7 runtime with TTS and speaker diarization disabled.')

if __name__=='__main__':main()
