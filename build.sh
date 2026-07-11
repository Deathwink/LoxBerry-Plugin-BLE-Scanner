#!/bin/sh
set -eu
VERSION="$(awk -F= '/^VERSION=/{print $2; exit}' plugin.cfg)"
ARCHIVE="dist/ble-scanner-mqtt-$VERSION.zip"
mkdir -p dist
rm -f "$ARCHIVE"
zip -qr "$ARCHIVE" plugin.cfg release.cfg prerelease.cfg dpkg daemon bin icons webfrontend \
    postinstall.sh preupgrade.sh postupgrade.sh README.md -x '*/.DS_Store'
printf 'Created %s\n' "$ARCHIVE"
