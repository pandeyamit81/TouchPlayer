#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="/boot/firmware/config.txt"
BACKUP_DIR="/root/touchplayer-dsi-backup-$(date +%Y%m%d-%H%M%S)"
XORG_DIR="/etc/X11/xorg.conf.d"
LIGHTDM_DIR="/etc/lightdm/lightdm.conf.d"
TARGET_USER="${SUDO_USER:-pi}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this script with sudo: sudo $0"
    exit 1
fi

mkdir -p "$BACKUP_DIR" "$XORG_DIR" "$LIGHTDM_DIR" "${TARGET_HOME}/.config/labwc"

if [[ -f "$CONFIG_FILE" ]]; then
    cp -a "$CONFIG_FILE" "$BACKUP_DIR/config.txt"
    sed -i \
        -e '/Waveshare HDMI LCD with XPT2046/d' \
        -e '/XPT2046 is handled by the Linux ads7846-compatible driver/d' \
        -e '/^[[:space:]]*dtoverlay=ads7846\([,[:space:]]\|$\)/d' \
        "$CONFIG_FILE"

    if ! grep -qE '^[[:space:]]*display_auto_detect=1[[:space:]]*$' "$CONFIG_FILE"; then
        printf '\ndisplay_auto_detect=1\n' >> "$CONFIG_FILE"
    fi
    if ! grep -qE '^[[:space:]]*dtoverlay=vc4-kms-v3d([,[:space:]]|$)' "$CONFIG_FILE"; then
        printf 'dtoverlay=vc4-kms-v3d\n' >> "$CONFIG_FILE"
    fi
fi

for legacy_file in \
    "$XORG_DIR/99-touchplayer-tinylcd.conf" \
    "$LIGHTDM_DIR/50-touchplayer-tinylcd.conf"; do
    if [[ -f "$legacy_file" ]]; then
        cp -a "$legacy_file" "$BACKUP_DIR/$(basename "$legacy_file")"
        rm -f "$legacy_file"
    fi
done

install -m 755 "$SCRIPT_DIR/scripts/touchplayer-kiosk.sh" /usr/local/bin/touchplayer-kiosk

LABWC_AUTOSTART="${TARGET_HOME}/.config/labwc/autostart"
if [[ ! -f "$LABWC_AUTOSTART" ]]; then
    printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' > "$LABWC_AUTOSTART"
elif ! grep -Fqx '/usr/local/bin/touchplayer-kiosk &' "$LABWC_AUTOSTART"; then
    printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' >> "$LABWC_AUTOSTART"
fi
chown -R "$TARGET_USER":"$TARGET_USER" "${TARGET_HOME}/.config/labwc"
chmod 755 "$LABWC_AUTOSTART"

if getent group input >/dev/null && ! id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx input; then
    usermod -aG input "$TARGET_USER"
fi

printf 'DSI display configuration installed for the DRM/KMS session.\n'
printf 'The panel mode is selected by the DSI firmware; this setup supports 800x480 panels.\n'
printf 'Backup: %s\n' "$BACKUP_DIR"
printf 'Reboot is required: sudo reboot\n'
printf 'Rollback: restore %s/config.txt and restore the backed-up legacy files if needed.\n' "$BACKUP_DIR"