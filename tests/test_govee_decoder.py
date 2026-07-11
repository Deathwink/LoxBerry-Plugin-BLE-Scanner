import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from govee_decoder import GoveeDecoder


class GoveeDecoderTests(unittest.TestCase):
    def test_decodes_supplied_h5075_advertisement(self):
        advertisement = SimpleNamespace(
            manufacturer_data={
                60552: bytes.fromhex("00050af46400"),
                76: bytes.fromhex("0215494e54454c4c495f524f434b535f48575075f2ffc2"),
            },
            service_uuids=["0000ec88-0000-1000-8000-00805f9b34fb"],
            service_data={},
        )
        decoded = GoveeDecoder().decode(
            "A4:C1:38:75:00:2B", "GVH5075_002B", -36, advertisement
        )
        self.assertEqual(decoded["decoder"], "govee_ble")
        self.assertEqual(decoded["model"], "H5075")
        self.assertEqual(decoded["values"]["temperature"]["value"], 33.0)
        self.assertEqual(decoded["values"]["humidity"]["value"], 48.4)
        self.assertEqual(decoded["values"]["battery"]["value"], 100)


if __name__ == "__main__":
    unittest.main()
