#!/usr/bin/env bash

set -u

SERIAL_DEVICE="${TOUCHPLAYER_CELLULAR_SERIAL:-/dev/serial0}"

echo '=== TouchPlayer SIM868 Cellular Diagnostic ==='
printf 'ModemManager: '
systemctl is-active ModemManager 2>/dev/null || true
printf 'NetworkManager: '
systemctl is-active NetworkManager 2>/dev/null || true

echo
echo '--- Modems ---'
if command -v mmcli >/dev/null 2>&1; then
    mmcli -L 2>&1 || true
    MODEM_PATH="$(mmcli -L 2>/dev/null | sed -n 's|.*\(/org/freedesktop/ModemManager1/Modem/[0-9][0-9]*\).*|\1|p' | head -n 1)"
    if [[ -n "$MODEM_PATH" ]]; then
        mmcli -m "$MODEM_PATH" 2>&1 || true
    fi
else
    echo 'mmcli is not installed.'
fi

echo
echo '--- Network devices ---'
nmcli -f DEVICE,TYPE,STATE,CONNECTION device 2>&1 || true

echo
echo '--- Cellular profile ---'
nmcli -f NAME,TYPE,DEVICE,AUTOCONNECT connection show 2>&1 | grep -E 'NAME|gsm|cellular' || true

echo
echo '--- Serial and WWAN devices ---'
ls -l "$SERIAL_DEVICE" /dev/ttyUSB* /dev/ttyACM* /dev/cdc-wdm* /dev/wwan* 2>&1 || true

echo
echo '--- UART PPP service ---'
systemctl is-enabled touchplayer-cellular.service 2>&1 || true
systemctl is-active touchplayer-cellular.service 2>&1 || true