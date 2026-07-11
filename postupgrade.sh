#!/bin/sh
set -eu
TEMP_NAME="$1"; PLUGIN_FOLDER="$3"; LB_BASE="$5"
CONFIG_DIR="$LB_BASE/config/plugins/$PLUGIN_FOLDER"
BACKUP_DIR="/tmp/${TEMP_NAME}_upgrade_ble_scanner"
mkdir -p "$CONFIG_DIR"
for file in pluginconfig.json; do
    [ ! -f "$BACKUP_DIR/$file" ] || cp -p "$BACKUP_DIR/$file" "$CONFIG_DIR/$file"
done
[ ! -d "$BACKUP_DIR" ] || rm -rf "$BACKUP_DIR"
exit 0
