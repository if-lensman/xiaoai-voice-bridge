import asyncio
import json
import math
import struct
import unittest
from unittest.mock import patch

import relay
from transport import HELLO, INPUT_PCM, OUTPUT_PCM, AUDIO_END, PLAYED, END, MAX_FRAME, OutputDecoder, read_frame


def frame(kind, body):
    return struct.pack('>BI', kind, len(body)) + body


class CodecTests(unittest.TestCase):
    def test_float_audio_with_silence_and_split_samples_never_becomes_integer_noise(self):
        values = [0.0] * 160 + [.2 * math.sin(i * .1) for i in range(640)]
        raw = b''.join(struct.pack('<f', x) for x in values)
        decoder = OutputDecoder(); pcm = bytearray()
        for start in range(0, len(raw), 7):
            pcm.extend(decoder.feed(raw[start:start+7]))
        decoder.finish()
        self.assertEqual(decoder.kind, 'f32le')
        expected = b''.join(struct.pack('<h', round(struct.unpack('<f', struct.pack('<f', x))[0] * 32767)) for x in values)
        self.assertEqual(bytes(pcm), expected)

    def test_integer_audio_remains_integer(self):
        raw = b''.join(struct.pack('<h', round(10000 * math.sin(i * .071))) for i in range(1000))
        decoder = OutputDecoder()
        self.assertEqual(decoder.feed(raw), raw)
        self.assertEqual(decoder.kind, 's16le')
        decoder.finish()

    def test_compressed_audio_is_rejected(self):
        with self.assertRaises(ValueError):
            OutputDecoder().feed(b'OggS' + bytes(256))


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_resumes_without_response_created_and_late_old_reply_is_ignored(self):
        from transport import CONTROL,RESET,STATUS
        import base64
        reader=asyncio.StreamReader()
        reader.feed_data(frame(HELLO,json.dumps({'token':'test','version':1,'rate':16000,'channels':2}).encode()))
        audio=base64.b64encode(b''.join(struct.pack('<f',.2*math.sin(i*.1)) for i in range(640))).decode()
        class Cloud:
            def __init__(self):self.events=asyncio.Queue()
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def send(self,raw):
                kind=json.loads(raw)['type'];events=[]
                if kind=='session.create':events=[{'type':'session.created'}]
                if kind=='speech_text_buffer.commit':events=[
                    {'type':'conversation.item.input_audio_transcription.completed','text':'旧问题','item_id':'q1'},
                    {'type':'response.output_text.delta','delta':'旧回复片段','response_id':'old'},
                    {'type':'response.output_audio.delta','delta':audio,'response_id':'old'}]
                if kind=='response.cancel':events=[
                    {'type':'response.output_audio.delta','delta':audio,'response_id':'old'},
                    {'type':'response.canceled','response_id':'old'},
                    {'type':'conversation.item.input_audio_transcription.started','item_id':'q2'},
                    {'type':'conversation.item.input_audio_transcription.completed','text':'新问题','item_id':'q2'},
                    {'type':'response.output_text.delta','delta':'迟到旧片段','response_id':'old'},
                    {'type':'response.output_text.delta','delta':'新的回答','response_id':'new'},
                    {'type':'response.output_audio.delta','delta':audio,'response_id':'new'},
                    {'type':'response.output_audio.done','response_id':'new'}]
                if kind=='session.close':events=[{'type':'session.closed'}]
                for event in events:await self.events.put(json.dumps(event))
            async def recv(self):return await self.events.get()
            def __aiter__(self):return self
            async def __anext__(self):return await self.recv()
        class Writer:
            def __init__(self):self.outputs=0;self.snapshots=[];self.resets=0
            def write(self,raw):
                kind=raw[0];body=raw[5:]
                if kind==OUTPUT_PCM:
                    self.outputs+=1
                    if self.outputs==1:reader.feed_data(frame(CONTROL,b'{"command":"interrupt"}'))
                if kind==RESET:self.resets+=1
                if kind==STATUS:
                    data=json.loads(body)
                    if data.get('type')=='ui':self.snapshots.append(data)
                if kind==AUDIO_END:reader.feed_data(frame(PLAYED,body)+frame(END,b''))
            async def drain(self):await asyncio.sleep(0)
        report={'captured_stereo_bytes':0,'uploaded_mono_packets':0,'played_pcm_bytes':0,
                'playback_turns_completed':0,'recognized_test_utterances':[]}
        writer=Writer()
        with patch('relay.connection',return_value=Cloud()):
            await asyncio.wait_for(relay.conversation(reader,writer,'test',10,report),3)
        self.assertEqual(writer.outputs,2);self.assertEqual(writer.resets,1)
        self.assertEqual(report['interrupts_confirmed'],1)
        last=writer.snapshots[-1]
        self.assertEqual(last['current']['user'],'新问题')
        self.assertEqual(last['current']['assistant'],'新的回答')
        self.assertEqual(last['previous']['assistant'],'旧回复片段')
        self.assertEqual(last['previous']['status'],'interrupted')

    async def test_goodbye_and_idle_close_cloud_and_release_endpoint(self):
        for goodbye in (False,True):
            with self.subTest(goodbye=goodbye):
                reader=asyncio.StreamReader()
                reader.feed_data(frame(HELLO,json.dumps({'token':'test','version':1,'rate':16000,'channels':2}).encode()))
                class Cloud:
                    def __init__(self):self.events=asyncio.Queue();self.closed=False
                    async def __aenter__(self):return self
                    async def __aexit__(self,*args):pass
                    async def send(self,raw):
                        event=json.loads(raw)
                        if event['type']=='session.create':await self.events.put(json.dumps({'type':'session.created'}))
                        if event['type']=='speech_text_buffer.commit' and goodbye:
                            await self.events.put(json.dumps({'type':'input_audio_transcription.completed','text':'豆包，再见。'}))
                        if event['type']=='session.close':
                            self.closed=True;await self.events.put(json.dumps({'type':'session.closed'}))
                    async def recv(self):return await self.events.get()
                    def __aiter__(self):return self
                    async def __anext__(self):return await self.recv()
                class Writer:
                    def __init__(self):self.kinds=[]
                    def write(self,raw):self.kinds.append(raw[0])
                    async def drain(self):pass
                report={'captured_stereo_bytes':0,'uploaded_mono_packets':0,'played_pcm_bytes':0,
                        'playback_turns_completed':0,'recognized_test_utterances':[]}
                cloud=Cloud();writer=Writer()
                with patch('relay.connection',return_value=cloud):
                    await asyncio.wait_for(relay.conversation(reader,writer,'test',10,report,
                        stop_on_goodbye=True,idle_seconds=.02),2)
                self.assertTrue(cloud.closed)
                self.assertTrue(report['cloud_session_closed_cleanly'])
                self.assertEqual(report['end_reason'],'user_goodbye' if goodbye else 'idle_timeout')
                self.assertEqual(writer.kinds[-1],END)
                self.assertEqual(report['uploaded_mono_packets'],0)

    async def test_oversized_frame_rejected_before_body_read(self):
        reader = asyncio.StreamReader(); reader.feed_data(struct.pack('>BI', INPUT_PCM, MAX_FRAME + 1))
        with self.assertRaises(ValueError): await read_frame(reader)

    async def test_incomplete_payload_rejected(self):
        reader = asyncio.StreamReader(); reader.feed_data(frame(INPUT_PCM, b'1234')[:-1]); reader.feed_eof()
        with self.assertRaises(asyncio.IncompleteReadError): await read_frame(reader)

    async def test_invalid_endpoint_token_cannot_open_cloud_session(self):
        reader = asyncio.StreamReader(); reader.feed_data(frame(HELLO, json.dumps({'token':'wrong'}).encode()))
        with patch('relay.connection') as cloud:
            with self.assertRaises(ValueError):
                await relay.conversation(reader, None, 'expected', 10, {})
            cloud.assert_not_called()

    async def test_half_duplex_drops_playback_capture_and_resumes_after_ack(self):
        reader = asyncio.StreamReader()
        reader.feed_data(frame(HELLO, json.dumps({'token':'test','version':1,'rate':16000,'channels':2}).encode()))
        capture = struct.pack('<hh', 100, 100) * 320
        class FakeCloud:
            def __init__(self): self.events = asyncio.Queue(); self.sent = []
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def send(self, raw):
                event=json.loads(raw); self.sent.append(event)
                if event['type']=='session.create': await self.events.put(json.dumps({'type':'session.created'}))
                if event['type']=='speech_text_buffer.commit':
                    import base64
                    audio=b''.join(struct.pack('<f',.2*math.sin(i*.1)) for i in range(640))
                    for item in [{'type':'response.created'}, {'type':'response.output_audio.delta','delta':base64.b64encode(audio).decode()},
                                 {'type':'response.output_audio.done'},{'type':'response.done'}]:
                        await self.events.put(json.dumps(item))
                if event['type']=='session.close': await self.events.put(json.dumps({'type':'session.closed'}))
            async def recv(self): return await self.events.get()
            def __aiter__(self): return self
            async def __anext__(self): return await self.recv()
        pending=[]
        class Writer:
            def write(self, raw):
                kind=raw[0]
                if kind==OUTPUT_PCM: reader.feed_data(frame(INPUT_PCM,capture))
                if kind==AUDIO_END:
                    reader.feed_data(frame(PLAYED,b'{"sequence":1}'))
                    async def user_reply():
                        await asyncio.sleep(.3)
                        reader.feed_data(frame(INPUT_PCM,capture)+frame(END,b''))
                    pending.append(asyncio.create_task(user_reply()))
            async def drain(self): await asyncio.sleep(.001)
        report={'captured_stereo_bytes':0,'uploaded_mono_packets':0,'played_pcm_bytes':0,
                'playback_turns_completed':0,'recognized_test_utterances':[]}
        cloud=FakeCloud()
        with patch('relay.connection',return_value=cloud):
            await asyncio.wait_for(relay.conversation(reader,Writer(),'test',10,report),3)
        await asyncio.gather(*pending)
        self.assertEqual(report['captured_stereo_bytes'],2560)
        self.assertEqual(report['uploaded_mono_packets'],1)
        self.assertEqual(report['playback_turns_completed'],1)
        self.assertTrue(report['cloud_session_closed_cleanly'])
        types=[x['type'] for x in cloud.sent]
        self.assertLess(types.index('input_audio_mute.commit'),types.index('input_audio_unmute.commit'))
        self.assertEqual(types.count('input_audio_buffer.append'),1)


if __name__=='__main__': unittest.main()
