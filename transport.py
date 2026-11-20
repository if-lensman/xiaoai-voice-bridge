"""Bounded framing for an authenticated temporary LAN session. No cloud keys."""
import asyncio
import math
import struct

HELLO, INPUT_PCM, OUTPUT_PCM, STATUS, ERROR, AUDIO_END, PLAYED, END = 0, 1, 2, 3, 4, 5, 6, 9
CONTROL, RESET = 7, 8
MAX_FRAME = 256 * 1024


async def read_frame(reader):
    header = await reader.readexactly(5)
    kind, size = struct.unpack('>BI', header)
    if size > MAX_FRAME:
        raise ValueError('Frame exceeds bound')
    return kind, await reader.readexactly(size)


async def write_frame(writer, kind, payload):
    if len(payload) > MAX_FRAME:
        raise ValueError('Frame exceeds bound')
    writer.write(struct.pack('>BI', kind, len(payload)) + payload)
    await writer.drain()


class OutputDecoder:
    """Choose PCM sample width from non-silent data, then keep it fixed."""
    def __init__(self):
        self.pending = bytearray()
        self.kind = None

    def feed(self, data):
        self.pending.extend(data)
        if self.pending.startswith(b'OggS'):
            raise ValueError('Compressed output received instead of PCM')
        if len(self.pending) > 256 * 1024:
            raise ValueError('Output sample format could not be determined')
        if self.kind is None and len(self.pending) >= 256:
            size = len(self.pending) // 4 * 4
            floats = [v[0] for v in struct.iter_unpack('<f', self.pending[:size])]
            good = [v for v in floats if math.isfinite(v) and -1 <= v <= 1]
            if len(good) >= len(floats) * .98 and any(abs(v) > .0001 for v in good):
                self.kind = 'f32le'
            elif len(good) < len(floats) * .95:
                self.kind = 's16le'
        if self.kind is None:
            return b''
        width = 4 if self.kind == 'f32le' else 2
        size = len(self.pending) // width * width
        raw = bytes(self.pending[:size]); del self.pending[:size]
        if self.kind == 's16le':
            return raw
        output = bytearray()
        for (value,) in struct.iter_unpack('<f', raw):
            if not math.isfinite(value) or not -1.01 <= value <= 1.01:
                raise ValueError('Invalid float PCM sample')
            output.extend(struct.pack('<h', round(max(-1, min(1, value)) * 32767)))
        return bytes(output)

    def finish(self):
        if self.kind is None and not any(self.pending):
            self.pending.clear()
            return
        if self.pending:
            raise ValueError('Truncated or ambiguous output PCM')
