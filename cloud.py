"""Doubao Seeduplex session setup. Keys stay in host-side private files."""
import asyncio
import json
import os
from pathlib import Path
import stat

from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

ROOT = Path(__file__).resolve().parent
ENDPOINT = 'wss://openspeech.bytedance.com/api/v3/duplex/realtime/dialogue'


def read_key():
    path = ROOT / '.secrets/volc-api-key'
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RuntimeError('Key file must have permission 0600')
    value = path.read_text().strip()
    if not value or any(c.isspace() for c in value):
        raise RuntimeError('Key file is empty or malformed')
    return value


def session_create():
    return {'type': 'session.create', 'session': {
        'model': '1.2.6.1',
        'instructions': '你是豆包，请用中文自然、简短地回答，每次一到三句话。',
        'audio': {'input': {'format': {'type': 'pcm', 'rate': 16000}},
                  'output': {'format': {'type': 'pcm', 'rate': 24000},
                             'voice': 'zh_female_vv_jupiter_bigtts'}}}}


def connection():
    return connect(ENDPOINT, additional_headers={'X-Api-Key': read_key()},
                   proxy=None, compression=None, open_timeout=12,
                   close_timeout=3, max_size=2 * 1024 * 1024, max_queue=16)


async def check():
    report = {'endpoint': ENDPOINT, 'audio_uploaded': False, 'session_created': False}
    try:
        async with asyncio.timeout(20):
            async with connection() as ws:
                report['websocket_authenticated'] = True
                await ws.send(json.dumps(session_create(), ensure_ascii=False))
                while True:
                    event = json.loads(await asyncio.wait_for(ws.recv(), 8))
                    kind = event.get('type')
                    if kind == 'error':
                        detail = event.get('error') or event
                        report['error_code'] = detail.get('code') if isinstance(detail, dict) else None
                        # Redact the credential even if an upstream message repeats it.
                        report['error_message'] = str(detail.get('message', '') if isinstance(detail, dict) else detail).replace(read_key(), '[redacted]')[:400]
                        break
                    if kind == 'session.created':
                        report['session_created'] = True
                        await ws.send(json.dumps({'type': 'session.close'}))
                    if kind == 'session.closed':
                        report['session_closed_cleanly'] = True
                        break
    except InvalidStatus as exc:
        report['http_status'] = exc.response.status_code
        report['exception_type'] = type(exc).__name__
        body = bytes(exc.response.body).decode('utf-8', errors='replace')
        report['response_detail'] = body.replace(read_key(), '[redacted]')[:700]
    except Exception as exc:
        report['exception_type'] = type(exc).__name__
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    os.umask(0o077)
    asyncio.run(check())
