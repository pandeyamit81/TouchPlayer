#!/usr/bin/env bash

set -euo pipefail

CONNECTION_NAME="${TOUCHPLAYER_CELLULAR_CONNECTION:-touchplayer-cellular}"
APN="${TOUCHPLAYER_CELLULAR_APN:-}"
USERNAME="${TOUCHPLAYER_CELLULAR_USERNAME:-}"
PASSWORD="${TOUCHPLAYER_CELLULAR_PASSWORD:-}"
SIM_PIN="${TOUCHPLAYER_CELLULAR_SIM_PIN:-}"
SERIAL_DEVICE="${TOUCHPLAYER_CELLULAR_SERIAL:-/dev/serial0}"
SERIAL_BAUD="${TOUCHPLAYER_CELLULAR_BAUD:-115200}"
CONFIG_FILE="/boot/firmware/config.txt"
CMDLINE_FILE="/boot/firmware/cmdline.txt"
BACKUP_DIR="/root/touchplayer-cellular-backup-$(date +%Y%m%d-%H%M%S)"
PREPARE_UART=false
PI_MODEL="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"

usage() {
    cat <<EOF
Usage: sudo $0 --apn PROVIDER_APN
    sudo $0 --prepare-uart

Configure a SIM868 cellular modem through ModemManager and
NetworkManager. The APN is supplied by the SIM/mobile carrier.

Optional environment variables:
  TOUCHPLAYER_CELLULAR_CONNECTION  NetworkManager profile name
  TOUCHPLAYER_CELLULAR_USERNAME    Carrier username, if required
  TOUCHPLAYER_CELLULAR_PASSWORD    Carrier password, if required
    TOUCHPLAYER_CELLULAR_SIM_PIN      SIM PIN, if the SIM is PIN-locked
    TOUCHPLAYER_CELLULAR_SERIAL       UART device (default: /dev/serial0)
    TOUCHPLAYER_CELLULAR_BAUD         UART speed (default: 115200)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apn)
            [[ $# -ge 2 ]] || { echo "--apn requires a value" >&2; exit 2; }
            APN="$2"
            shift 2
            ;;
        --prepare-uart)
            PREPARE_UART=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this script with sudo: sudo $0 --apn PROVIDER_APN" >&2
    exit 1
fi

if [[ -z "$APN" && "$PREPARE_UART" != true ]]; then
    echo "A carrier APN is required." >&2
    usage >&2
    exit 2
fi

echo "Installing cellular modem support..."
apt-get update
apt-get install -y \
    modemmanager \
    network-manager \
    libqmi-utils \
    libmbim-utils \
    ppp \
    usb-modeswitch \
    usb-modeswitch-data

systemctl enable --now NetworkManager ModemManager

MODEM_PATH=""
if [[ "$PREPARE_UART" != true ]]; then
    for _ in {1..20}; do
        MODEM_PATH="$(mmcli -L 2>/dev/null | sed -n 's|.*\(/org/freedesktop/ModemManager1/Modem/[0-9][0-9]*\).*|\1|p' | head -n 1)"
        [[ -n "$MODEM_PATH" ]] && break
        sleep 1
    done
fi

if [[ -z "$MODEM_PATH" ]]; then
    if [[ "$PREPARE_UART" == true ]]; then
        echo "Preparing the SIM868 GPIO UART path without an APN."
    else
        echo "No USB modem detected; configuring the SIM868 GPIO UART path."
    fi
    mkdir -p "$BACKUP_DIR" /etc/ppp/peers /etc/chatscripts
    [[ -f "$CONFIG_FILE" ]] && cp -a "$CONFIG_FILE" "$BACKUP_DIR/config.txt"
    [[ -f "$CMDLINE_FILE" ]] && cp -a "$CMDLINE_FILE" "$BACKUP_DIR/cmdline.txt"

    if ! grep -qE '^[[:space:]]*enable_uart=1[[:space:]]*$' "$CONFIG_FILE"; then
        printf '\nenable_uart=1\n' >> "$CONFIG_FILE"
    fi
    if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
        if ! grep -qE '^[[:space:]]*dtoverlay=uart0-pi5([,[:space:]]|$)' "$CONFIG_FILE"; then
            printf 'dtoverlay=uart0-pi5\n' >> "$CONFIG_FILE"
        fi
    else
        sed -i -E '/^[[:space:]]*dtoverlay=uart0-pi5([,[:space:]]|$)/d' "$CONFIG_FILE"
    fi
    if [[ -f "$CMDLINE_FILE" ]]; then
        sed -i -E 's/(^| )console=serial0,[^ ]+//g; s/  +/ /g' "$CMDLINE_FILE"
    fi

    if [[ "$PREPARE_UART" == true ]]; then
        systemctl daemon-reload
        echo "SIM868 UART prepared. Reboot, then rerun with --apn PROVIDER_APN to create the PPP service."
        echo "Backup: $BACKUP_DIR"
        exit 0
    fi

    cat > /etc/chatscripts/touchplayer-cellular <<EOF
ABORT 'BUSY'
ABORT 'NO CARRIER'
ABORT 'NO DIALTONE'
ABORT 'ERROR'
ABORT '+CME ERROR'
TIMEOUT 8
'' AT
OK ATE0
OK AT+CFUN=1
OK AT+CGATT=1
OK AT+CGDCONT=1,"IP","$APN"
OK ATD*99***1#
CONNECT ''
EOF

    {
        printf '%s\n' "$SERIAL_DEVICE $SERIAL_BAUD"
        printf '%s\n' 'local' 'lock' 'modem' 'nocrtscts' 'noauth' 'persist' 'nodetach'
        printf '%s\n' 'maxfail 0' 'holdoff 5' 'defaultroute' 'usepeerdns' 'noipv6'
        printf '%s\n' 'ipcp-accept-local' 'ipcp-accept-remote' 'noipdefault'
        if [[ -n "$USERNAME" ]]; then
            printf 'user %s\n' "$USERNAME"
        fi
        if [[ -n "$PASSWORD" ]]; then
            printf 'password %s\n' "$PASSWORD"
        fi
        printf '%s\n' 'connect "/usr/sbin/chat -v -f /etc/chatscripts/touchplayer-cellular"'
    } > /etc/ppp/peers/touchplayer-cellular

    cat > /etc/systemd/system/touchplayer-cellular.service <<'EOF'
[Unit]
Description=TouchPlayer SIM868 GSM/GPRS PPP connection
After=NetworkManager.service network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
ExecStart=/usr/sbin/pppd call touchplayer-cellular
SuccessExitStatus=5
TimeoutStopSec=12
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    chmod 600 /etc/ppp/peers/touchplayer-cellular /etc/chatscripts/touchplayer-cellular
    cat > /etc/sudoers.d/touchplayer-sms <<'EOF'
pi ALL=(root) NOPASSWD: /usr/bin/python3 /opt/touchplayer/scripts/sim868_pwrkey.py, /usr/bin/systemctl stop --no-block touchplayer-cellular.service, /usr/bin/systemctl start touchplayer-cellular.service, /usr/bin/systemctl is-active --quiet touchplayer-cellular.service
EOF
    chmod 440 /etc/sudoers.d/touchplayer-sms
    visudo -cf /etc/sudoers.d/touchplayer-sms >/dev/null
    systemctl daemon-reload
    systemctl enable touchplayer-cellular.service
    if [[ -e "$SERIAL_DEVICE" ]]; then
        systemctl restart touchplayer-cellular.service
        echo "SIM868 UART PPP configuration installed and started."
    else
        echo "SIM868 UART PPP configuration installed. Reboot is required to enable $SERIAL_DEVICE."
    fi
    echo "Backup: $BACKUP_DIR"
    exit 0
fi

echo "Detected modem: $MODEM_PATH"
mmcli -m "$MODEM_PATH" --enable >/dev/null 2>&1 || true

if nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION_NAME"; then
    nmcli connection modify "$CONNECTION_NAME" \
        gsm.apn "$APN" \
        gsm.number "*99#" \
        connection.autoconnect yes \
        connection.autoconnect-retries 0 \
        ipv4.method auto \
        ipv4.never-default no \
        ipv4.route-metric 700 \
        ipv6.method auto \
        ipv6.never-default no \
        ipv6.route-metric 700
else
    nmcli connection add type gsm ifname "*" con-name "$CONNECTION_NAME" apn "$APN"
    nmcli connection modify "$CONNECTION_NAME" \
        gsm.number "*99#" \
        connection.autoconnect yes \
        connection.autoconnect-retries 0 \
        ipv4.never-default no \
        ipv4.route-metric 700 \
        ipv6.never-default no \
        ipv6.route-metric 700
fi

if [[ -n "$USERNAME" ]]; then
    nmcli connection modify "$CONNECTION_NAME" gsm.username "$USERNAME"
fi
if [[ -n "$PASSWORD" ]]; then
    nmcli connection modify "$CONNECTION_NAME" gsm.password "$PASSWORD"
fi
if [[ -n "$SIM_PIN" ]]; then
    nmcli connection modify "$CONNECTION_NAME" gsm.pin "$SIM_PIN"
fi

echo "Activating cellular connection..."
nmcli connection up "$CONNECTION_NAME"
echo "Cellular profile '$CONNECTION_NAME' is configured for APN '$APN' and will autoconnect at boot."