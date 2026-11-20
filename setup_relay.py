"""Create private relay configuration. No network calls and no secret output."""
import argparse
import getpass
import ipaddress
import json
import os
from pathlib import Path
import secrets

def address(value):
    ip=ipaddress.IPv4Address(value)
    if not any(ip in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
        raise argparse.ArgumentTypeError('Use an RFC1918 private IPv4 address')
    return str(ip)

def main():
    parser=argparse.ArgumentParser(description='Prepare your own NAS and speaker configuration; credentials stay local.')
    parser.add_argument('--relay-ip',type=address)
    parser.add_argument('--speaker-ip',type=address);args=parser.parse_args()
    root=Path(__file__).resolve().parent;private=root/'private';private.mkdir(mode=0o700,exist_ok=True)
    if any((private/name).exists() for name in ('volc-api-key','service-config.json')):
        raise SystemExit('Existing private configuration found; not overwritten.')
    try:
        args.relay_ip=args.relay_ip or address(input('NAS LAN IPv4: ').strip())
        args.speaker_ip=args.speaker_ip or address(input('LX04 LAN IPv4: ').strip())
    except (ValueError,argparse.ArgumentTypeError):
        raise SystemExit('Use valid private LAN IPv4 addresses; no configuration saved.')
    key=getpass.getpass('Doubao speech API Key (hidden): ').strip()
    if not key or not key.isascii() or any(c.isspace() for c in key) or len(key)>4096:
        raise SystemExit('Invalid Key format; no files saved.')
    config={'host':args.relay_ip,'port':18878,'token':secrets.token_hex(32),'seconds':0,'voice_interrupt':True}
    (private/'volc-api-key').write_text(key)
    (private/'service-config.json').write_text(json.dumps(config))
    for path in private.iterdir():path.chmod(0o600)
    (root/'data').mkdir(mode=0o700,exist_ok=True)
    (root/'.env').write_text('RELAY_BIND_IP='+args.relay_ip+'\nDEVICE_IP='+args.speaker_ip+'\n')
    (root/'.env').chmod(0o600)
    print('Private files created; no cloud connection made. Configure NAS ownership before Docker startup.')

if __name__=='__main__':os.umask(0o077);main()
