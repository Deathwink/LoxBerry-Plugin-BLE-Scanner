# BLE Scanner MQTT for LoxBerry 4

A LoxBerry 4 plugin that scans Bluetooth Low Energy advertisements through BlueZ, decodes supported sensor protocols, and publishes the results through the built-in LoxBerry MQTT Gateway.

## Features

- Python 3 in a plugin-private virtual environment; no Python 2 dependencies.
- BLE scanning through `bleak` and the BlueZ D-Bus API.
- MQTT broker, port, and credentials are read automatically from LoxBerry.
- Filters for MAC address, device name regular expression, and minimum RSSI.
- MQTT publishing is allow-list based by default: select individual MAC addresses in the WebUI, or disable the MAC filter to publish all devices.
- Each detected device has an expandable raw/decoded JSON view in the WebUI.
- Configurable presence timeout.
- Raw JSON includes name, address, RSSI, TX power, UUIDs, manufacturer data, and service data.
- Decoded numeric and binary values are published as retained MQTT topics.
- Momentary events are published without retain.
- Italian and English WebUI using the native LoxBerry language system.
- User configuration, filters, Xiaomi bindkeys, and excluded MAC addresses are preserved during upgrades.

## Supported decoders

### Govee

Uses `govee-ble==1.2.0`, the parser used by the official Home Assistant Govee Bluetooth integration. It supports recognized Govee thermometers, hygrometers, multi-probe sensors, PM2.5 and CO₂ monitors, motion and presence sensors, door/window sensors, vibration sensors, pressure sensors, and buttons.

### Xiaomi

Uses `xiaomi-ble==1.11.0`, as used by the official Home Assistant Xiaomi BLE integration. Supported families include Xiaomi, Mijia, Qingping, Flower Care, and compatible MiBeacon devices. Depending on the model, decoded data can include temperature, humidity, battery, illuminance, soil moisture, conductivity, formaldehyde, weight, impedance, motion, opening, smoke, locks, buttons, and events.

Encrypted MiBeacon devices require a bindkey. Enter one device per line in the WebUI:

```text
AA:BB:CC:DD:EE:FF=00112233445566778899aabbccddeeff
```

Both 12-byte keys (24 hexadecimal characters) and 16-byte keys (32 hexadecimal characters) are accepted. Bindkeys are stored in `pluginconfig.json` with mode `0600` and are preserved during upgrades.

Xiaomi BLE Mesh identity frames are recognized separately from ordinary MiBeacon sensor frames. For example, product ID `0x1040` is reported as the probable `WX10ZM` / Mijia Mosquito Repellent 2. The plugin publishes the MiBeacon version, frame control, product ID, counter, embedded MAC, Mesh/registration/encryption flags, and remaining payload. It explicitly marks that passive operational state is unavailable when no MiBeacon object is included; controlling the device or reading consumable/battery state requires an active Xiaomi Mesh connection.

### Oral-B

Uses `oralb-ble==1.1.0`, the parser used by the official Home Assistant Oral-B integration. Passive advertisements are supported for Triumph D36, Smart Series D21/D700, Pro Series D601, Genius Series D701/D706, and iO Series toothbrushes.

Published values can include:

- brushing time;
- toothbrush state;
- brushing mode;
- pressure;
- current sector and sector timer;
- number of sectors;
- brushing active status;
- signal strength.

Battery data in the upstream library requires an active GATT connection. This plugin intentionally performs passive scanning only, so it does not connect to a toothbrush to poll its battery.

### Raw BLE fallback

Devices not recognized by a specialized decoder are still published as raw BLE JSON when they pass the configured filters.

## Installation

1. Configure and enable the LoxBerry MQTT Gateway.
2. Run `./build.sh`, or use the ZIP file generated in `dist/`.
3. Upload the ZIP from **Plugin management → Install plugin**.
4. Reboot LoxBerry when requested.
5. Open **BLE Scanner MQTT**, configure the filters, and save.

Internet access is required during installation to create the virtual environment and install the pinned Python dependencies.

## MQTT topics

With the default base topic `loxberry/ble_scanner`:

| Topic | Content | Retained |
| --- | --- | --- |
| `loxberry/ble_scanner/availability` | `online` / `offline` | yes |
| `loxberry/ble_scanner/events` | Latest raw/decoded device JSON | no |
| `.../device/aa_bb_cc_dd_ee_ff/json` | Complete device data | yes |
| `.../device/aa_bb_cc_dd_ee_ff/rssi` | RSSI in dBm | yes |
| `.../device/aa_bb_cc_dd_ee_ff/presence` | `1` present, `0` absent | yes |
| `.../device/aa_bb_cc_dd_ee_ff/<value>` | Dynamically decoded value | yes |
| `.../device/aa_bb_cc_dd_ee_ff/event/<event>` | Momentary decoded event | no |

Binary values use `1` and `0`. Manufacturer and service-data bytes in JSON are represented as hexadecimal strings.

## WebUI languages

The WebUI uses `LoxBerry::System::readlanguage` with:

- `templates/lang/language_en.ini`
- `templates/lang/language_it.ini`

English is the automatic fallback when the selected LoxBerry language is not available.

## Device publishing policy

The MAC allow-list is enabled by default and starts empty, so a new installation does not send discovered devices to MQTT automatically. The WebUI continues collecting discovery data locally. Expand the JSON column to identify a device, select **Publish**, and save. To publish every device that passes the RSSI/name filters, disable **Publish selected MAC addresses only**.

## Upgrade behavior

`pluginconfig.json` is saved and restored by the upgrade scripts. It contains all settings, filters, excluded MAC addresses, and Xiaomi bindkeys. `devices.json` is only a discovery cache and is rebuilt automatically after an upgrade.

## Diagnostics

```sh
bluetoothctl show
systemctl status bluetooth
```

If no controller is shown, check the USB adapter, VM passthrough, and RF blocks with `rfkill`.
