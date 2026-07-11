#!/bin/sh
set -eu
BIN_DIR="$(CDPATH='' cd "$(dirname "$0")" && pwd)"
PLUGIN_FOLDER="${BIN_DIR##*/}"
LB_ROOT="${BIN_DIR%/bin/plugins/*}"
CONFIG_DIR="$LB_ROOT/config/plugins/$PLUGIN_FOLDER"
LOG_DIR="$LB_ROOT/log/plugins/$PLUGIN_FOLDER"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/pluginconfig.json" ]; then
  cp "$BIN_DIR/default_config.json" "$CONFIG_DIR/pluginconfig.json"
  chmod 600 "$CONFIG_DIR/pluginconfig.json"
fi
# The LoxBerry daemon manager starts this script as root. Repair leftovers from
# earlier releases so the authenticated WebUI can atomically replace config.
chown -R loxberry:loxberry "$CONFIG_DIR"
exec "$BIN_DIR/venv/bin/python" "$BIN_DIR/ble_scanner.py" \
  --config "$CONFIG_DIR/pluginconfig.json" \
  --general "$LB_ROOT/config/system/general.json" \
  --status "$CONFIG_DIR/status.json" \
  --devices "$CONFIG_DIR/devices.json" \
  --log "$LOG_DIR/ble_scanner.log"
