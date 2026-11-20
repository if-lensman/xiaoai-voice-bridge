"""Authenticated LX04 realtime audio, text and interruption session."""
import asyncio
import base64
import contextlib
import hmac
import json
import os
import time

from cloud import connection, session_create
from pcm import PcmAdapter
from session_policy import is_goodbye
from screen_text import ScreenText
from transport import CONTROL, RESET
from transport import HELLO, INPUT_PCM, OUTPUT_PCM, STATUS, ERROR, AUDIO_END, PLAYED, END, OutputDecoder, read_frame, write_frame

PORT = 18878
DEVICE_IP = os.environ.get('DEVICE_IP', '192.0.2.41')



async def conversation(reader, writer, token, seconds, report, *, stop_on_goodbye=False, idle_seconds=None, greeting='你好，我是豆包。请说吧。'):
    kind, raw = await asyncio.wait_for(read_frame(reader), 8)
    if kind != HELLO or len(raw) > 2048:
        raise ValueError('Invalid endpoint greeting')
    hello = json.loads(raw)
    if not hmac.compare_digest(str(hello.get('token', '')), token):
        raise ValueError('Endpoint token rejected')
    if (hello.get('rate'), hello.get('channels'), hello.get('version')) != (16000, 2, 1):
        raise ValueError('Unexpected endpoint audio format')
    report['device_connected'] = True
    adapter = PcmAdapter(gain=12)
    speaking = False; sequence = 0; waiting_ack = None; response_has_audio = False; resume_at = 0.0
    cancel_pending=False; suppress_output=False; cancel_started=0.0
    decoder = OutputDecoder()
    last_activity = time.monotonic()
    screen = ScreenText(greeting); screen_state='listening'; last_screen_sent=0.0
    async def show(state=None,force=True):
        nonlocal screen_state,last_screen_sent
        if state is not None:screen_state=state
        now=time.monotonic()
        if force or now-last_screen_sent>=.12:
            await write_frame(writer,STATUS,json.dumps(screen.snapshot(screen_state),ensure_ascii=False).encode())
            last_screen_sent=now
            report['screen_updates']=report.get('screen_updates',0)+1
    send_lock = asyncio.Lock()

    async with connection() as ws:
        async def send(message):
            async with send_lock:
                await ws.send(json.dumps(message, ensure_ascii=False))

        await send(session_create())
        while True:
            event = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if event.get('type') == 'error':
                raise RuntimeError('Cloud session rejected: ' + str((event.get('error') or {}).get('code', 'unknown')))
            if event.get('type') == 'session.created':
                break
        report['cloud_session_created'] = True
        await write_frame(writer, STATUS, b'{"type":"ready"}')
        await show('listening')
        await send({'type': 'speech_text_buffer.commit', 'text': greeting})

        async def microphone():
            nonlocal speaking, waiting_ack, resume_at, last_activity, cancel_pending, suppress_output, cancel_started
            while True:
                kind, body = await read_frame(reader)
                if kind == END:
                    return
                if kind == CONTROL:
                    command=json.loads(body).get('command')
                    if command=='end':
                        report['end_reason']='touch_end';return
                    if command!='interrupt':raise ValueError('Unknown control')
                    report['interrupt_requests']=report.get('interrupt_requests',0)+1
                    waiting_ack=None;last_activity=time.monotonic()
                    screen.interrupt()
                    if speaking and not cancel_pending:
                        cancel_pending=True;suppress_output=True;cancel_started=time.monotonic()
                        await show('interrupting')
                        await send({'type':'response.cancel'})
                    elif not speaking:
                        await write_frame(writer,RESET,b'');await show('listening')
                    continue
                if kind == PLAYED:
                    ack = json.loads(body)
                    if waiting_ack is not None and ack.get('sequence') == waiting_ack:
                        waiting_ack = None; speaking = False; resume_at = time.monotonic() + .25
                        await send({'type': 'input_audio_unmute.commit'})
                        report['playback_turns_completed'] += 1
                        screen.complete()
                        last_activity = time.monotonic()
                        await show('listening')
                    continue
                if kind != INPUT_PCM or len(body) > 5120 or len(body) % 4:
                    raise ValueError('Invalid stereo capture frame')
                report['captured_stereo_bytes'] += len(body)
                for packet in adapter.feed(body):
                    if not speaking and time.monotonic() >= resume_at:
                        await send({'type': 'input_audio_buffer.append', 'audio': base64.b64encode(packet).decode()})
                        report['uploaded_mono_packets'] += 1

        async def responses():
            nonlocal speaking, sequence, waiting_ack, response_has_audio, last_activity, cancel_pending, suppress_output, decoder, resume_at
            async for raw in ws:
                event = json.loads(raw); kind = event.get('type', '')
                if kind.endswith(('input_audio_transcription.started','input_audio_transcription.delta')):
                    last_activity=time.monotonic()
                if kind=='response.canceled':
                    if not cancel_pending and not screen.response_allowed(event):continue
                    screen.interrupt()
                    cancel_pending=False;speaking=False;waiting_ack=None;response_has_audio=False
                    decoder=OutputDecoder();last_activity=time.monotonic()
                    resume_at=time.monotonic()+.35
                    await send({'type':'input_audio_unmute.commit'})
                    await write_frame(writer,RESET,b'');await show('listening')
                    report['interrupts_confirmed']=report.get('interrupts_confirmed',0)+1
                    continue
                # Older models need not emit response.created. New user speech
                # reopens output after the cancellation acknowledgement as well.
                new_user = kind.endswith(('input_audio_transcription.started','input_audio_transcription.delta','input_audio_transcription.completed'))
                if new_user and not cancel_pending:suppress_output=False
                if kind=='response.created' and not cancel_pending and screen.response_allowed(event):suppress_output=False
                if suppress_output and kind.startswith('response.'):
                    continue
                if kind.startswith('response.') and not screen.response_allowed(event):
                    continue
                if screen.event(event):
                    if kind.endswith('input_audio_transcription.started'):screen_state_next='listening'
                    elif kind.endswith('input_audio_transcription.completed'):screen_state_next='thinking'
                    elif kind.startswith('response.'):screen_state_next='speaking'
                    else:screen_state_next=None
                    await show(screen_state_next,force=not kind.endswith('.delta'))
                    if kind.endswith('transcription.completed') and screen.user:
                        report['screen_user_turns']=report.get('screen_user_turns',0)+1
                    if kind=='response.output_text.done' and screen.assistant:
                        report['screen_answer_turns']=report.get('screen_answer_turns',0)+1
                if kind == 'error':
                    raise RuntimeError('Cloud error code: ' + str((event.get('error') or {}).get('code', 'unknown')))
                if kind == 'response.created':
                    response_has_audio = False
                    if not speaking:
                        speaking = True
                        await send({'type': 'input_audio_mute.commit'})
                if kind == 'response.output_audio.delta':
                    if not speaking:
                        speaking = True
                        await send({'type': 'input_audio_mute.commit'})
                    response_has_audio = True
                    audio = decoder.feed(base64.b64decode(event['delta'], validate=True))
                    if audio:
                        await write_frame(writer, OUTPUT_PCM, audio)
                        report['played_pcm_bytes'] += len(audio)
                if kind == 'response.output_audio.done':
                    decoder.finish(); sequence += 1; waiting_ack = sequence
                    await write_frame(writer, AUDIO_END, json.dumps({'sequence': sequence}).encode())
                if kind == 'response.done' and speaking and not response_has_audio and waiting_ack is None:
                    speaking = False
                    await send({'type': 'input_audio_unmute.commit'})
                    await show('listening')
                if kind in ('conversation.item.input_audio_transcription.completed', 'input_audio_transcription.completed'):
                    text = event.get('transcript', event.get('text', ''))
                    if text: last_activity = time.monotonic()
                    if text:
                        report['recognized_utterance_count']=report.get('recognized_utterance_count',0)+1
                    if stop_on_goodbye and is_goodbye(text):
                        report['end_reason'] = 'user_goodbye'
                        return
                if kind == 'response.output_text.done' and event.get('text'):
                    report['response_text_count']=report.get('response_text_count',0)+1
                if kind == 'session.closed':
                    return

        tasks = [asyncio.create_task(microphone()), asyncio.create_task(responses())]
        async def cancel_guard():
            while True:
                await asyncio.sleep(.5)
                if cancel_pending and time.monotonic()-cancel_started>5:
                    raise RuntimeError('Cloud cancel acknowledgement timed out')
        tasks.append(asyncio.create_task(cancel_guard()))
        if idle_seconds is not None:
            async def idle_guard():
                while True:
                    await asyncio.sleep(.5)
                    if not speaking and time.monotonic() - last_activity >= idle_seconds:
                        report['end_reason'] = 'idle_timeout'
                        return
            tasks.append(asyncio.create_task(idle_guard()))
        try:
            done, pending = await asyncio.wait(tasks, timeout=seconds + 8 if seconds else None, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            with contextlib.suppress(Exception):
                await send({'type': 'session.close'})
                async with asyncio.timeout(3):
                    while True:
                        event = json.loads(await ws.recv())
                        if event.get('type') == 'session.closed':
                            report['cloud_session_closed_cleanly'] = True
                            break
            report['output_encoding'] = decoder.kind
            report['input_clipped_samples'] = adapter.clipped
            if stop_on_goodbye:
                with contextlib.suppress(Exception):await show('standby')
                with contextlib.suppress(Exception): await write_frame(writer, END, b'')
