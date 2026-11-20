"""Check local readiness without opening a cloud session or using credentials."""
import json
from pathlib import Path
import socket

def main():
    report=json.loads(Path('/app/outputs/service-status.json').read_text())
    if not report.get('running'):raise SystemExit(1)
    with socket.create_connection(('127.0.0.1',18878),timeout=1):pass

if __name__=='__main__':main()
