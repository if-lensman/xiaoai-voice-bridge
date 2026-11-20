"""Install the terminal on an explicitly selected, authorized root-ADB LX04."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

PACKAGE='local.lx04.doubao.screen'
REMOTE='/data/data/'+PACKAGE+'/files/service-config.json'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True)
    parser.add_argument('--apk',required=True,type=Path);parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--adb',default=shutil.which('adb') or 'adb');args=parser.parse_args()
    def adb(*command,allow_error=False):
        result=subprocess.run([args.adb,'-s',args.serial,*command],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        if result.returncode and not allow_error:raise RuntimeError('ADB operation failed: '+command[0])
        return result.stdout.decode(errors='replace')
    if adb('shell','getprop ro.product.model').strip()!='LX04':raise SystemExit('Only LX04 has been validated; no changes made.')
    if 'uid=0(root)' not in adb('shell','id'):raise SystemExit('Authorized root ADB is required; no changes made.')
    if not args.apk.is_file():raise SystemExit('Build the APK first.')
    config=json.loads(args.config.read_text())
    if not config.get('token') or config.get('seconds')!=0:raise SystemExit('Use configuration from setup_relay.py.')
    backup=Path('private/device-backups')/time.strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,mode=0o700)
    exists=adb('shell','test -f '+REMOTE+' && echo PRESENT',allow_error=True).strip()=='PRESENT'
    if exists:
        adb('pull',REMOTE,str(backup/'service-config.json'));(backup/'service-config.json').chmod(0o600)
    adb('install','-r',str(args.apk));adb('shell','pm grant '+PACKAGE+' android.permission.RECORD_AUDIO')
    adb('shell','am stopservice -n '+PACKAGE+'/.VoiceService',allow_error=True);time.sleep(2)
    adb('shell','mkdir -p /data/data/'+PACKAGE+'/files')
    adb('push',str(args.config),REMOTE+'.new')
    adb('shell','chown $(stat -c %u:%g /data/data/'+PACKAGE+') /data/data/'+PACKAGE+'/files '+REMOTE+'.new && chmod 700 /data/data/'+PACKAGE+'/files && chmod 600 '+REMOTE+'.new && mv '+REMOTE+'.new '+REMOTE+' && restorecon -RF /data/data/'+PACKAGE+'/files')
    adb('shell','am start-foreground-service -n '+PACKAGE+'/.VoiceService',allow_error=True);time.sleep(4)
    state=adb('shell','dumpsys activity services '+PACKAGE)
    if 'isForeground=true' not in state:raise RuntimeError('Service did not enter foreground; inspect device logs. Backup preserved.')
    print('Terminal service started. No system/boot partitions were written; private backup preserved when present.')

if __name__=='__main__':main()
