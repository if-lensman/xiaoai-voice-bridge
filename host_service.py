"""Persistent private-LAN relay. Opens a cloud session only after authenticated wake."""
import asyncio
import contextlib
import json
import logging
import os
import signal
from cloud import ROOT,read_key
from relay import DEVICE_IP,PORT,conversation
from transport import ERROR,write_frame

async def main():
    read_key()
    config=json.loads((ROOT/'.secrets/service-config.json').read_text())
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    logger=logging.getLogger('doubao');logger.setLevel(logging.WARNING)
    handler=logging.StreamHandler();handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'));logger.addHandler(handler)
    active=set();busy=False;finished=asyncio.Event()
    status={'mode':'persistent','running':False,'active_session':False,'completed_sessions':0}
    def save():
        target=out/'service-status.json';temp=target.with_suffix('.tmp')
        temp.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');temp.replace(target)
    async def handle(reader,writer):
        nonlocal busy
        if writer.get_extra_info('peername')[0]!=DEVICE_IP or busy:
            writer.close();return
        busy=True;task=asyncio.current_task();active.add(task)
        status['active_session']=True;save()
        report={'captured_stereo_bytes':0,'uploaded_mono_packets':0,'played_pcm_bytes':0,
                'playback_turns_completed':0}
        try:
            await conversation(reader,writer,config['token'],None,report,stop_on_goodbye=True,idle_seconds=45,
                               greeting=config.get('greeting','你好，我是豆包。请说吧。'))
        except Exception as exc:
            status['last_error_type']=type(exc).__name__
            logger.warning('SESSION_ERROR %s',type(exc).__name__)
            with contextlib.suppress(Exception):await write_frame(writer,ERROR,b'{}')
        finally:
            writer.close()
            with contextlib.suppress(Exception):await writer.wait_closed()
            if report.get('device_connected'):status['completed_sessions']+=1
            status['active_session']=False;busy=False;active.discard(task);save()
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,finished.set)
    listen_host=os.environ.get('LISTEN_HOST',config['host'])
    server=await asyncio.start_server(handle,listen_host,PORT)
    status['running']=True;save()
    try:
        async with server:await finished.wait()
    finally:
        for task in list(active):task.cancel()
        if active:await asyncio.gather(*list(active),return_exceptions=True)
        status['running']=False;save()

if __name__=='__main__':
    os.umask(0o077)
    try:asyncio.run(main())
    except Exception as exc:raise SystemExit('Relay stopped: '+type(exc).__name__)
