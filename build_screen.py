"""Build the Android local-wake, audio and dialogue-screen app."""
import os
from pathlib import Path
import subprocess
import zipfile
import shutil
from build_config import ROOT,SDK,JDK

def main():
    out=ROOT/'android/build/screen';out.mkdir(parents=True,exist_ok=True)
    classes=out/'classes';dex=out/'dex'
    for folder in (classes,dex):
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir()
    tools=SDK/'build-tools/34.0.0';platform=SDK/'platforms/android-34/android.jar'
    env=os.environ.copy();env['JAVA_HOME']=str(JDK)
    subprocess.run([str(JDK/'bin/javac'),'--release','8','-cp',str(platform),'-d',str(classes),
                    *map(str,(ROOT/'screen').glob('*.java')),*map(str,(ROOT/'android').glob('*.java'))],check=True)
    subprocess.run([str(tools/'d8'),'--min-api','27','--lib',str(platform),'--output',str(dex),
                    *map(str,classes.rglob('*.class'))],env=env,check=True)
    unsigned=out/'screen-unsigned.apk'
    subprocess.run([str(tools/'aapt2'),'link','-o',str(unsigned),'--manifest',str(ROOT/'screen/AndroidManifest.xml'),
                    '-I',str(platform)],check=True)
    with zipfile.ZipFile(unsigned,'a',zipfile.ZIP_DEFLATED) as archive:
        archive.write(dex/'classes.dex','classes.dex')
        for path in (ROOT/'android/build/kws/model').iterdir():archive.write(path,'assets/model/'+path.name)
        for path in (ROOT/'android/build/kws').glob('*.so'):archive.write(path,'lib/armeabi-v7a/'+path.name)
    aligned=out/'screen-aligned.apk'
    notices=ROOT/'licenses'
    with zipfile.ZipFile(unsigned,'a',zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT/'LICENSE','assets/licenses/project-MIT.txt')
        archive.write(ROOT/'THIRD_PARTY_NOTICES.md','assets/licenses/THIRD_PARTY_NOTICES.md')
        for path in notices.rglob('*'):
            if path.is_file():archive.write(path,'assets/licenses/'+str(path.relative_to(notices)))
    # Adding notices changes ZIP offsets, so align again before signing.
    subprocess.run([str(tools/'zipalign'),'-f','4',str(unsigned),str(aligned)],check=True)
    keystore=Path(os.environ.get('APK_SIGNING_KEYSTORE',str(Path.home()/'.android/debug.keystore')))
    password_file=os.environ.get('APK_SIGNING_PASSWORD_FILE')
    password='file:'+password_file if password_file else 'pass:android'
    subprocess.run([str(tools/'apksigner'),'sign','--ks',str(keystore),
                    '--ks-pass',password,'--out',str(out/'doubao-screen.apk'),str(aligned)],env=env,check=True)
    subprocess.run([str(tools/'apksigner'),'verify',str(out/'doubao-screen.apk')],env=env,check=True)
    print('Built signed dialogue APK with third-party notices.')

if __name__=='__main__':main()
