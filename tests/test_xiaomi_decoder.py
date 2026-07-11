import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from xiaomi_decoder import XiaomiDecoder, parse_bindkeys


class XiaomiDecoderTests(unittest.TestCase):
    def test_decodes_unencrypted_lywsdcgq(self):
        advertisement = SimpleNamespace(
            manufacturer_data={},
            service_data={
                "0000fe95-0000-1000-8000-00805f9b34fb":
                    b"P \xaa\x01\xa3\xbf.;4-X\r\x10\x04\xb4\x00\x95\x02\n\x10\x01;"
            },
            service_uuids=["0000fe95-0000-1000-8000-00805f9b34fb"],
        )
        decoded = XiaomiDecoder().decode(
            "58:2D:34:3B:2E:BF", "Test", -60, advertisement
        )
        self.assertEqual(decoded["decoder"], "xiaomi_ble")
        self.assertEqual(decoded["model"], "LYWSDCGQ")
        self.assertEqual(decoded["values"]["temperature"]["value"], 18.0)
        self.assertEqual(decoded["values"]["humidity"]["value"], 66.1)
        self.assertEqual(decoded["values"]["battery"]["value"], 59.0)

    def test_parse_bindkeys(self):
        keys = parse_bindkeys(
            "AA:BB:CC:DD:EE:FF=00112233445566778899aabbccddeeff\n"
            "11:22:33:44:55:66=00112233445566778899aabb\n"
        )
        self.assertEqual(len(keys["AA:BB:CC:DD:EE:FF"]), 16)
        self.assertEqual(len(keys["11:22:33:44:55:66"]), 12)

    def test_decodes_mesh_identity_without_inventing_sensor_state(self):
        advertisement = SimpleNamespace(
            manufacturer_data={},
            service_data={"0000fe95-0000-1000-8000-00805f9b34fb": bytes.fromhex("9055401001cff565319e640e00")},
            service_uuids=["0000fe95-0000-1000-8000-00805f9b34fb"],
        )
        decoded = XiaomiDecoder().decode(
            "64:9E:31:65:F5:CF", "Mesh Mi Mosq V2", -98, advertisement
        )
        self.assertEqual(decoded["decoder"], "xiaomi_mesh_identity")
        self.assertEqual(decoded["model"], "WX10ZM")
        self.assertEqual(decoded["identity"]["product_id"], "0x1040")
        self.assertEqual(decoded["identity"]["mac"], "64:9E:31:65:F5:CF")
        self.assertTrue(decoded["identity"]["mesh"])
        self.assertFalse(decoded["identity"]["object_included"])
        self.assertFalse(decoded["identity"]["passive_state_available"])


if __name__ == "__main__":
    unittest.main()
