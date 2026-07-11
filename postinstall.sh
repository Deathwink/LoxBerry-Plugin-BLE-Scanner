#!/bin/sh
set -eu
PDIR="$3"
PLUGIN_BIN="$LBHOMEDIR/bin/plugins/$PDIR"
VENV="$PLUGIN_BIN/venv"

[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check --no-cache-dir \
    'bleak==0.22.3' 'paho-mqtt==2.1.0' 'govee-ble==1.2.0' \
    'xiaomi-ble==1.11.0' 'oralb-ble==1.1.0'
chmod 755 "$VENV"
exit 0
