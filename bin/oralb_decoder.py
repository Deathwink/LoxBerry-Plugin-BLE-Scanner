#!/usr/bin/env python3
"""Adapter from Bleak advertisements to the oralb-ble parser used by Home Assistant."""
from __future__ import annotations

from typing import Dict

from bluetooth_sensor_state_data import BluetoothServiceInfo
from oralb_ble.parser import OralBBluetoothDeviceData

from govee_decoder import entity_key, json_value


class OralBDecoder:
    def __init__(self):
        self.parsers: Dict[str, OralBBluetoothDeviceData] = {}

    def decode(self, address: str, name: str, rssi: int, advertisement) -> dict | None:
        if 220 not in advertisement.manufacturer_data:
            return None
        service_info = BluetoothServiceInfo(
            name=name, address=address, rssi=rssi,
            manufacturer_data=dict(advertisement.manufacturer_data),
            service_uuids=list(advertisement.service_uuids),
            service_data=dict(advertisement.service_data), source="loxberry",
        )
        parser = self.parsers.setdefault(address, OralBBluetoothDeviceData())
        update = parser.update(service_info)
        if update is None or not update.devices:
            return None
        primary = update.devices.get(None) or next(iter(update.devices.values()))
        result = {
            "decoder": "oralb_ble", "model": primary.model,
            "device_name": primary.name, "values": {},
            "binary_values": {}, "events": {},
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
        return result
