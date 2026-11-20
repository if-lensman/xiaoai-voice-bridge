import math
import struct
import unittest

from pcm import PcmAdapter


class PcmTests(unittest.TestCase):
    def test_stereo_transport_splits_do_not_change_audio(self):
        raw = b''.join(struct.pack('<hh', i - 500, 500 - i) for i in range(1000))
        whole = PcmAdapter(); expected = whole.feed(raw) + whole.finish()
        split = PcmAdapter(); actual = []
        for offset in range(0, len(raw), 7):
            actual.extend(split.feed(raw[offset:offset + 7]))
        actual.extend(split.finish())
        self.assertEqual(actual, expected)
        self.assertTrue(all(len(packet) == 640 for packet in actual))

    def test_channel_choice_does_not_cancel_opposite_phase_microphones(self):
        raw = struct.pack('<hh', 1200, -1200) * 320
        adapter = PcmAdapter(channel=0, gain=1, highpass_hz=0)
        self.assertEqual(adapter.feed(raw), [struct.pack('<h', 1200) * 320])

    def test_full_scale_input_saturates_instead_of_wrapping(self):
        raw = struct.pack('<hh', 32000, -32000) * 320
        adapter = PcmAdapter(gain=32, highpass_hz=0)
        self.assertEqual(adapter.feed(raw), [struct.pack('<h', 32767) * 320])
        self.assertEqual(adapter.clipped, 320)

    def test_highpass_rejects_constant_bias(self):
        adapter = PcmAdapter(gain=1)
        packets = adapter.feed(struct.pack('<hh', 1000, 1000) * 16000)
        last = struct.unpack('<320h', packets[-1])
        self.assertLess(max(abs(v) for v in last), 2)

    def test_truncated_stereo_frame_is_not_silently_accepted(self):
        adapter = PcmAdapter()
        adapter.feed(b'\x01\x00\x02')
        with self.assertRaises(ValueError):
            adapter.finish()


if __name__ == '__main__':
    unittest.main()
