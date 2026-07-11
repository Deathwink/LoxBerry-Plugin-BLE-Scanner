#!/usr/bin/env python3
"""Adapter from Bleak advertisements to the govee-ble parser used by Home Assistant."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict

from bluetooth_sensor_state_data import BluetoothServiceInfo
from govee_ble.parser import GoveeBluetoothDeviceData


def safe_key(value) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", str(value).lower()).strip("_")


def entity_key(device_key) -> str:
    key = safe_key(device_key.key)
    if device_key.device_id is not None:
        key += "_" + safe_key(device_key.device_id)
    return key


def json_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


class GoveeDecoder:
    """Keep one stateful upstream parser per Bluetooth address."""

    def __init__(self):
        self.parsers: Dict[str, GoveeBluetoothDeviceData] = {}

    def decode(self, address: str, name: str, rssi: int, advertisement) -> dict | None:
        service_info = BluetoothServiceInfo(
            name=name,
            address=address,
            rssi=rssi,
            manufacturer_data=dict(advertisement.manufacturer_data),
            service_uuids=list(advertisement.service_uuids),
            service_data=dict(advertisement.service_data),
            source="loxberry",
        )
        parser = self.parsers.setdefault(address, GoveeBluetoothDeviceData())
        update = parser.update(service_info)
        if update is None or not update.devices:
            return None

        primary = update.devices.get(None) or next(iter(update.devices.values()))
        result = {
            "decoder": "govee_ble",
            "model": primary.model,
            "device_name": primary.name,
            "values": {},
            "binary_values": {},
            "events": {},
        }
        for key, value in update.entity_values.items():
            native = value.native_value
            if native == "error":
                continue
            item = {"value": json_value(native), "name": value.name}
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
                "type": event.event_type,
                "name": event.name,
                "properties": json_value(event.event_properties),
            }
        return result
