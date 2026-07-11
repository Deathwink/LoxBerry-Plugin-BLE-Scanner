import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from oralb_decoder import OralBDecoder


class OralBDecoderTests(unittest.TestCase):
    def test_decodes_passive_toothbrush_advertisement(self):
        advertisement = SimpleNamespace(
            manufacturer_data={220: b"\x02\x01\x08\x02 \x00\x00\x01\x01\x00\x04"},
            service_uuids=[], service_data={},
        )
        decoded = OralBDecoder().decode(
            "78:DB:2F:C2:48:BE", "Oral-B Toothbrush", -63, advertisement
        )
        self.assertEqual(decoded["decoder"], "oralb_ble")
        self.assertEqual(decoded["model"], "Triumph D36")
        self.assertIn("time", decoded["values"])
        self.assertIn("toothbrush_state", decoded["values"])
        self.assertIn("pressure", decoded["values"])
        self.assertIn("mode", decoded["values"])
        self.assertIn("brushing", decoded["binary_values"])


if __name__ == "__main__":
    unittest.main()
