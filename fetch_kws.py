"""Fetch pinned upstream Android runtime and offline model, verify before extraction."""
import base64
import hashlib
import subprocess
import tarfile
from build_config import ROOT
from build_kws import MODEL

ASSETS=[('v1.13.5','sherpa-onnx-v1.13.5-android.tar.bz2',
         '635eee004bf12d5881789876ea01964a6ef10dc74ccf317271ba9388d8718a84'),
        ('kws-models',MODEL+'.tar.bz2',
         'b812a043aef628a6915f89cb9a94e55f8e87e89ff904b516f822d7e0a3e6de2b')]

def main():
    folder=ROOT/'vendor';folder.mkdir(exist_ok=True)
    for release,name,digest in ASSETS:
        subprocess.run(['gh','release','download',release,'--repo','k2-fsa/sherpa-onnx',
                        '--pattern',name,'--dir',str(folder),'--skip-existing'],check=True)
        archive=folder/name
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Upstream asset checksum mismatch: '+name)
        with tarfile.open(archive) as tar:
            members=[m for m in tar.getmembers()
                     if (release=='kws-models' or m.name.startswith('./jniLibs/armeabi-v7a/'))
                     and 'test_wavs' not in m.name.split('/')]
            tar.extractall(folder,members=members,filter='data')
    raw=subprocess.check_output(['gh','api','repos/k2-fsa/sherpa-onnx/contents/sherpa-onnx/c-api/c-api.h?ref=v1.13.5','--jq','.content'])
    (folder/'c-api.h').write_bytes(base64.b64decode(raw))
    print('Verified and extracted pinned KWS assets.')

if __name__=='__main__':main()
