#!/bin/sh
set -eu
TEMP_NAME="$1"; PLUGIN_FOLDER="$3"; LB_BASE="$5"
CONFIG_DIR="$LB_BASE/config/plugins/$PLUGIN_FOLDER"
BACKUP_DIR="/tmp/${TEMP_NAME}_upgrade_ble_scanner"
mkdir -p "$BACKUP_DIR"
for file in pluginconfig.json devices.json; do
    [ ! -f "$CONFIG_DIR/$file" ] || cp -p "$CONFIG_DIR/$file" "$BACKUP_DIR/$file"
done
exit 0
