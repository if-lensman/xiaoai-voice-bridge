"""LX04 PCM16 stereo -> Doubao PCM16 mono, exactly 20 ms per packet.

No microphone, network, or filesystem access. Caller owns the session lifetime.
"""
import math
import struct

SAMPLE_RATE = 16000
FRAMES_PER_PACKET = 320
OUTPUT_PACKET_BYTES = 640


class PcmAdapter:
    def __init__(self, *, channel=0, gain=12.0, highpass_hz=60.0):
        if channel not in (0, 1):
            raise ValueError('LX04 input channel must be 0 or 1')
        if not 0 < gain <= 32:
            raise ValueError('Gain must be in (0, 32]')
        if not 0 <= highpass_hz <= 200:
            raise ValueError('High-pass frequency must be 0..200 Hz')
        self.channel, self.gain = channel, gain
        self.alpha = math.exp(-2 * math.pi * highpass_hz / SAMPLE_RATE) if highpass_hz else None
        self.pending_input = bytearray()
        self.pending_output = bytearray()
        self.previous_input = self.previous_output = 0.0
        self.samples = self.clipped = 0

    def feed(self, data):
        """Accept arbitrarily split, interleaved two-channel little-endian PCM16."""
        self.pending_input.extend(data)
        complete = len(self.pending_input) // 4 * 4
        block = bytes(self.pending_input[:complete])
        del self.pending_input[:complete]
        for left, right in struct.iter_unpack('<hh', block):
            value = (left, right)[self.channel]
            if self.alpha is not None:
                filtered = self.alpha * (self.previous_output + value - self.previous_input)
                self.previous_input, self.previous_output = value, filtered
                value = filtered
            value = round(value * self.gain)
            if value < -32768 or value > 32767:
                self.clipped += 1
            self.pending_output.extend(struct.pack('<h', max(-32768, min(32767, value))))
            self.samples += 1
        packets = []
        while len(self.pending_output) >= OUTPUT_PACKET_BYTES:
            packets.append(bytes(self.pending_output[:OUTPUT_PACKET_BYTES]))
            del self.pending_output[:OUTPUT_PACKET_BYTES]
        return packets

    def finish(self):
        """Pad only a complete final sample packet. Reject truncated stereo frames."""
        if self.pending_input:
            raise ValueError('Truncated stereo PCM input')
        if not self.pending_output:
            return []
        packet = bytes(self.pending_output).ljust(OUTPUT_PACKET_BYTES, b'\0')
        self.pending_output.clear()
        return [packet]
