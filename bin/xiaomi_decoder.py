#!/usr/bin/env python3
"""Adapter from Bleak advertisements to the xiaomi-ble parser used by Home Assistant."""
from __future__ import annotations

from typing import Dict

from home_assistant_bluetooth import BluetoothServiceInfo
from xiaomi_ble.parser import XiaomiBluetoothDeviceData

from govee_decoder import entity_key, json_value


def parse_bindkeys(text: str) -> Dict[str, bytes]:
    """Parse one MAC=hex bindkey per line, ignoring comments and invalid rows."""
    result = {}
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")) or "=" not in line:
            continue
        address, value = (part.strip() for part in line.split("=", 1))
        address = address.upper()
        try:
            key = bytes.fromhex(value)
        except ValueError:
            continue
        if len(key) in (12, 16):
            result[address] = key
    return result


class XiaomiDecoder:
    def __init__(self):
        self.parsers: Dict[str, XiaomiBluetoothDeviceData] = {}
        self.parser_keys: Dict[str, bytes | None] = {}

    def decode(self, address: str, name: str, rssi: int, advertisement, bindkeys: str = "") -> dict | None:
        mesh = self.decode_mesh_identity(address, name, advertisement)
        if mesh is not None:
            return mesh
        keys = parse_bindkeys(bindkeys)
        bindkey = keys.get(address.upper())
        parser = self.parsers.get(address)
        if parser is None:
            parser = XiaomiBluetoothDeviceData(bindkey=bindkey)
            self.parsers[address] = parser
            self.parser_keys[address] = bindkey
        elif self.parser_keys.get(address) != bindkey:
            parser.set_bindkey(bindkey)
            self.parser_keys[address] = bindkey

        service_info = BluetoothServiceInfo(
            name=name,
            address=address,
            rssi=rssi,
            manufacturer_data=dict(advertisement.manufacturer_data),
            service_uuids=list(advertisement.service_uuids),
            service_data=dict(advertisement.service_data),
            source="loxberry",
        )
        if not parser.supported(service_info):
            return None
        update = parser.update(service_info)
        if update is None or not update.devices:
            return None
        primary = update.devices.get(None) or next(iter(update.devices.values()))
        result = {
            "decoder": "xiaomi_ble",
            "model": primary.model,
            "device_name": primary.name,
            "encrypted": parser.encryption_scheme.value != "none",
            "bindkey_verified": bool(parser.bindkey_verified),
            "values": {}, "binary_values": {}, "events": {},
        }
        for key, value in update.entity_values.items():
            item = {"value": json_value(value.native_value), "name": value.name}
            description = update.entity_descriptions.get(key)
            unit = getattr(description, "native_unit_of_measurement", None)
            if unit is not None:
                item["unit"] = getattr(unit, "value", str(unit))
            result["values"][entity_key(key)] = item
        for key, value in update.binary_entity_values.items():
            result["binary_values"][entity_key(key)] = {
                "value": bool(value.native_value), "name": value.name
            }
        for key, event in update.events.items():
            result["events"][entity_key(key)] = {
                "type": event.event_type, "name": event.name,
                "properties": json_value(event.event_properties),
            }
        return result

    @staticmethod
    def decode_mesh_identity(address: str, name: str, advertisement) -> dict | None:
        service_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
        data = advertisement.service_data.get(service_uuid)
        if data is None or len(data) < 11:
            return None
        frame_control = int.from_bytes(data[0:2], "little")
        if not bool((frame_control >> 7) & 1):
            return None
        product_id = int.from_bytes(data[2:4], "little")
        mac = ":".join(f"{byte:02X}" for byte in reversed(data[5:11]))
        model = "WX10ZM" if product_id == 0x1040 else f"Xiaomi Mesh 0x{product_id:04X}"
        return {
            "decoder": "xiaomi_mesh_identity", "model": model,
            "device_name": name or model, "values": {}, "binary_values": {}, "events": {},
            "identity": {
                "frame_control": f"0x{frame_control:04X}",
                "product_id": f"0x{product_id:04X}",
                "frame_counter": data[4], "mac": mac,
                "mibeacon_version": frame_control >> 12,
                "authentication_mode": (frame_control >> 10) & 0x03,
                "solicited": bool((frame_control >> 9) & 1),
                "registered": bool((frame_control >> 8) & 1),
                "mesh": True,
                "object_included": bool((frame_control >> 6) & 1),
                "capability_included": bool((frame_control >> 5) & 1),
                "mac_included": bool((frame_control >> 4) & 1),
                "encrypted": bool((frame_control >> 3) & 1),
                "request_timing": bool(frame_control & 1),
                "remaining_data": data[11:].hex(),
                "passive_state_available": False,
            },
        }
