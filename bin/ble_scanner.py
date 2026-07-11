#!/usr/bin/env python3
"""Scan BLE advertisements with BlueZ and publish them through LoxBerry MQTT."""
import argparse
import asyncio
import json
import logging
import re
import signal
import time
from pathlib import Path

from bleak import BleakScanner
import paho.mqtt.client as mqtt
from govee_decoder import GoveeDecoder

DEFAULTS = {"enabled": 1, "mqtt_topic": "loxberry/ble_scanner", "scan_window": 10,
            "scan_pause": 2, "offline_after": 60, "minimum_rssi": -100,
            "publish_unknown": 1, "mac_filter": "", "name_filter": "", "disabled_macs": []}

def read_json(path, fallback=None):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else dict(fallback or {})
    except (OSError, ValueError):
        return dict(fallback or {})

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)

def mqtt_settings(path):
    mqtt_cfg = read_json(path).get("Mqtt", {})
    host, port = mqtt_cfg.get("Brokerhost"), mqtt_cfg.get("Brokerport")
    if not host or not port:
        raise RuntimeError("Broker MQTT non configurato nel MQTT Gateway LoxBerry")
    return str(host), int(port), str(mqtt_cfg.get("Brokeruser") or ""), str(mqtt_cfg.get("Brokerpass") or "")

def safe_id(address):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", address).lower()

def hex_map(values):
    return {str(key): bytes(value).hex() for key, value in values.items()}

class Bridge:
    def __init__(self, args):
        self.args, self.client, self.connected = args, None, False
        self.seen, self.stop = {}, asyncio.Event()
        self.govee = GoveeDecoder()
        self.config_mtime = -1

    def config(self):
        cfg = DEFAULTS.copy(); cfg.update(read_json(self.args.config))
        topic = str(cfg["mqtt_topic"]).strip().strip("/")
        if not topic or "+" in topic or "#" in topic: raise RuntimeError("Topic MQTT non valido")
        cfg["mqtt_topic"] = topic
        return cfg

    def set_status(self, message, **extra):
        value = {"running": True, "mqtt_connected": self.connected, "message": message,
                 "devices_seen": len(self.seen), "updated_at": int(time.time())}
        value.update(extra); write_json(self.args.status, value)

    def connect(self, cfg):
        host, port, user, password = mqtt_settings(self.args.general)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="loxberry-ble-scanner", clean_session=True)
        if user: client.username_pw_set(user, password)
        client.will_set(cfg["mqtt_topic"] + "/availability", "offline", retain=True)
        client.on_connect = lambda c, u, f, rc, p: setattr(self, "connected", int(rc) == 0)
        client.on_disconnect = lambda c, u, df, rc, p: setattr(self, "connected", False)
        client.connect(host, port, 30); client.loop_start(); self.client = client
        limit = time.monotonic() + 5
        while not client.is_connected() and time.monotonic() < limit: time.sleep(0.05)
        self.connected = client.is_connected()
        client.publish(cfg["mqtt_topic"] + "/availability", "online", retain=True)

    def publish(self, cfg, address, payload):
        base = f"{cfg['mqtt_topic']}/device/{safe_id(address)}"
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.client.publish(base + "/json", body, retain=True)
        self.client.publish(base + "/rssi", str(payload["rssi"]), retain=True)
        self.client.publish(base + "/presence", "1", retain=True)
        decoded = payload.get("decoded")
        if isinstance(decoded, dict):
            for field, item in decoded.get("values", {}).items():
                self.client.publish(base + "/" + field, str(item["value"]), retain=True)
            for field, item in decoded.get("binary_values", {}).items():
                self.client.publish(base + "/" + field, "1" if item["value"] else "0", retain=True)
            for field, item in decoded.get("events", {}).items():
                self.client.publish(base + "/event/" + field, json.dumps(item), retain=False)
        self.client.publish(cfg["mqtt_topic"] + "/events", body, retain=False)

    async def cycle(self, cfg):
        devices = await BleakScanner.discover(timeout=max(1, float(cfg["scan_window"])), return_adv=True)
        now = int(time.time()); macs = [x.strip().upper() for x in str(cfg["mac_filter"]).split(",") if x.strip()]
        disabled = {str(x).strip().upper() for x in cfg.get("disabled_macs", []) if str(x).strip()}
        name_re = re.compile(str(cfg["name_filter"]), re.I) if str(cfg["name_filter"]).strip() else None
        known = read_json(self.args.devices)
        for _, (device, adv) in devices.items():
            address, name = device.address.upper(), adv.local_name or device.name or ""
            known[address] = {"address": address, "name": name, "rssi": adv.rssi, "last_seen": now}
            if address in disabled:
                base = f"{cfg['mqtt_topic']}/device/{safe_id(address)}"
                for field in ("json", "rssi", "temperature", "humidity", "battery"):
                    self.client.publish(base + "/" + field, "", retain=True)
                self.client.publish(base + "/presence", "0", retain=True)
                self.seen.pop(address, None)
                continue
            if adv.rssi < int(cfg["minimum_rssi"]): continue
            if macs and address not in macs: continue
            if name_re and not name_re.search(name): continue
            if not cfg["publish_unknown"] and not name: continue
            payload = {"address": address, "name": name, "rssi": adv.rssi, "tx_power": adv.tx_power,
                       "service_uuids": list(adv.service_uuids), "manufacturer_data": hex_map(adv.manufacturer_data),
                       "service_data": hex_map(adv.service_data), "present": True, "last_seen": now}
            decoded = self.govee.decode(address, name, adv.rssi, adv)
            if decoded is not None:
                payload["decoded"] = decoded
            self.seen[address] = now; self.publish(cfg, address, payload)
        if len(known) > 500:
            known = dict(sorted(known.items(), key=lambda item: item[1].get("last_seen", 0), reverse=True)[:500])
        write_json(self.args.devices, known)
        offline_after = max(5, int(cfg["offline_after"]))
        for address, last_seen in list(self.seen.items()):
            if now - last_seen > offline_after:
                self.client.publish(f"{cfg['mqtt_topic']}/device/{safe_id(address)}/presence", "0", retain=True)
                del self.seen[address]
        self.connected = bool(self.client and self.client.is_connected())
        self.set_status("Scansione attiva", last_scan=now)

    async def run(self):
        cfg = self.config(); self.connect(cfg)
        while not self.stop.is_set():
            try:
                cfg = self.config()
                if cfg["enabled"]: await self.cycle(cfg)
                else: self.set_status("Scanner disabilitato")
            except Exception as exc:
                logging.exception("Scan cycle failed"); self.set_status(str(exc), error=True)
            try: await asyncio.wait_for(self.stop.wait(), timeout=max(1, float(cfg["scan_pause"])))
            except asyncio.TimeoutError: pass
        if self.client:
            self.client.publish(cfg["mqtt_topic"] + "/availability", "offline", retain=True).wait_for_publish(2)
            self.client.disconnect(); self.client.loop_stop()

def main():
    parser = argparse.ArgumentParser()
    for name in ("config", "general", "status", "devices", "log"): parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    bridge = Bridge(args); loop = asyncio.new_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try: loop.add_signal_handler(sig, bridge.stop.set)
        except NotImplementedError: pass
    loop.run_until_complete(bridge.run())

if __name__ == "__main__": main()
