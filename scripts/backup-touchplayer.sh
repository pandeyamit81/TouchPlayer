#!/usr/bin/env bash
# Create a recovery-ready TouchPlayer backup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${TOUCHPLAYER_SOURCE_DIR:-${SCRIPT_DIR}}"
DEPLOY_DIR="${TOUCHPLAYER_DEPLOY_DIR:-/opt/touchplayer}"
DESTINATION="${TOUCHPLAYER_BACKUP_DIR:-/home/pi/touchplayer-backups}"
INCLUDE_MEDIA=false
BACKUP_OWNER_UID="${SUDO_UID:-}"
BACKUP_OWNER_GID="${SUDO_GID:-}"

usage() {
    cat <<EOF
Usage: sudo $0 [options]

Create a compressed TouchPlayer backup containing the source code, deployed
copy, system configuration, application data, package lists, and a restore
script.

Options:
  --destination DIR  Store the backup archive in DIR.
  --include-media    Include /home/pi/Music in the backup.
  -h, --help         Show this help.

Examples:
  sudo $0 --destination /media/pi/TOUCHPLAYER_BACKUP
  sudo $0 --destination /mnt/backup --include-media

The archive is protected with mode 600. Keep it private because it may contain
Wi-Fi, Samba, PPP, and SMS configuration data.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --destination)
            [[ $# -ge 2 ]] || { echo "--destination requires a directory" >&2; exit 2; }
            DESTINATION="$2"
            shift 2
            ;;
        --include-media)
            INCLUDE_MEDIA=true
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
    echo "Run this script with sudo so it can capture system configuration." >&2
    exit 1
fi

SOURCE_DIR="$(readlink -f "${SOURCE_DIR}")"
DEPLOY_DIR="$(readlink -f "${DEPLOY_DIR}" 2>/dev/null || printf '%s' "${DEPLOY_DIR}")"
DESTINATION="$(readlink -m "${DESTINATION}")"

case "${DESTINATION}/" in
    "${SOURCE_DIR}/"*|"${DEPLOY_DIR}/"*)
        echo "The backup destination must not be inside the source or deployed directory." >&2
        exit 1
        ;;
esac

[[ -d "${SOURCE_DIR}" ]] || { echo "Source directory does not exist: ${SOURCE_DIR}" >&2; exit 1; }
mkdir -p "${DESTINATION}"

BACKUP_NAME="touchplayer-backup-$(hostname -s)-$(date -u +%Y%m%dT%H%M%SZ)"
WORK_DIR="$(mktemp -d "${DESTINATION}/.${BACKUP_NAME}.XXXXXX")"
ARCHIVE_PATH="${DESTINATION}/${BACKUP_NAME}.tar.gz"
ROOT_DIR="${WORK_DIR}/root"

cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

mkdir -p "${ROOT_DIR}" "${WORK_DIR}/metadata"
PI_ROOT_DIR="${WORK_DIR}/raspberry-pi"
mkdir -p "${PI_ROOT_DIR}"

copy_path() {
    copy_path_to "${ROOT_DIR}" "$1"
}

copy_path_to() {
    local destination_root="$1"
    local path="$2"
    if [[ ! -e "${path}" && ! -L "${path}" ]]; then
        return 0
    fi
    mkdir -p "${destination_root}$(dirname "${path}")"
    cp -a "${path}" "${destination_root}$(dirname "${path}")/"
}

copy_tree() {
    local source="$1"
    local target="$2"
    [[ -d "${source}" ]] || return 0
    mkdir -p "${ROOT_DIR}/${target}"
    tar -C "${source}" \
        --exclude='./venv' \
        --exclude='./.venv' \
        --exclude='./frontend/node_modules' \
        --exclude='./frontend/dist' \
        --exclude='./__pycache__' \
        --exclude='./.pytest_cache' \
        --exclude='./frontend/.vite' \
        --exclude='./*/__pycache__' \
        --exclude='./cache/artwork' \
        --exclude='./cache/thumbnails' \
        --exclude='*.pyc' \
        -cf - . | tar -C "${ROOT_DIR}/${target}" -xf -
}

copy_tree "${SOURCE_DIR}" "${SOURCE_DIR#/}"
if [[ -d "${DEPLOY_DIR}" && "${DEPLOY_DIR}" != "${SOURCE_DIR}" ]]; then
    copy_tree "${DEPLOY_DIR}" "${DEPLOY_DIR#/}"
fi

# System configuration installed by install.sh, update.sh, and configure-cellular.sh.
for path in \
    /etc/mpd.conf \
    /etc/ppp/peers/touchplayer-cellular \
    /etc/chatscripts/touchplayer-cellular \
    /etc/sudoers.d/touchplayer-sms \
    /etc/nginx/sites-available/touchplayer \
    /etc/nginx/sites-enabled/touchplayer \
    /etc/samba/smb.conf \
    /etc/samba/smb.conf.d \
    /etc/NetworkManager/system-connections \
    /etc/wpa_supplicant/wpa_supplicant.conf \
    /etc/hostname \
    /etc/hosts \
    /etc/fstab \
    /etc/systemd/system/mpd.service.d \
    /home/pi/.config/labwc \
    /etc/xdg/lxsession/LXDE-pi \
    /usr/local/bin/touchplayer-kiosk \
    /var/lib/mpd \
    /var/lib/samba \
    /var/lib/bluetooth; do
    copy_path "${path}"
done

for path in /etc/systemd/system/touchplayer*.service; do
    copy_path "${path}"
done

for path in \
    /etc/dhcpcd.conf \
    /etc/modules \
    /etc/modprobe.d \
    /etc/udev/rules.d \
    /etc/raspi-config \
    /etc/default/keyboard \
    /etc/default/raspi-firmware \
    /boot/config.txt \
    /boot/cmdline.txt \
    /boot/firmware/config.txt \
    /boot/firmware/cmdline.txt \
    /boot/firmware/usercfg.txt \
    /boot/firmware/sysconf.txt; do
    copy_path_to "${PI_ROOT_DIR}" "${path}"
done

if [[ "${INCLUDE_MEDIA}" == true ]]; then
    copy_tree "/home/pi/Music" "home/pi/Music"
else
    echo "/home/pi/Music (omitted; use --include-media to include it)" > "${WORK_DIR}/metadata/omitted-media.txt"
fi

# Capture recovery information without embedding command output in the source tree.
{
    printf 'Created (UTC): %s\n' "$(date -u --iso-8601=seconds)"
    printf 'Hostname: %s\n' "$(hostname)"
    printf 'Source directory: %s\n' "${SOURCE_DIR}"
    printf 'Deployed directory: %s\n' "${DEPLOY_DIR}"
    printf 'Media included: %s\n' "${INCLUDE_MEDIA}"
    printf 'Raspberry Pi configuration included: true\n'
    printf 'Kernel: %s\n' "$(uname -a)"
    printf '\nInstalled packages:\n'
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort
    printf '\nManually installed packages:\n'
    apt-mark showmanual 2>/dev/null | sort || true
    printf '\nTouchPlayer service enablement:\n'
    systemctl list-unit-files 'touchplayer*' --no-legend 2>/dev/null || true
    printf '\nCurrent service states:\n'
    systemctl --no-pager --plain --full status \
        touchplayer-api touchplayer-cellular touchplayer-indexer \
        touchplayer-mpd-listener touchplayer-bluetooth mpd nginx smbd nmbd \
        2>&1 || true
    printf '\nNetwork addresses:\n'
    ip -brief address 2>/dev/null || true
    printf '\nStorage:\n'
    df -h 2>/dev/null || true
} > "${WORK_DIR}/metadata/manifest.txt"

{
    printf 'Raspberry Pi model:\n'
    tr -d '\0' < /proc/device-tree/model 2>/dev/null || true
    printf '\nKernel:\n'
    uname -a
    printf '\nvcgencmd version:\n'
    vcgencmd version 2>/dev/null || true
    printf '\nvcgencmd configuration:\n'
    vcgencmd get_config int 2>/dev/null || true
    printf '\nvcgencmd throttling:\n'
    vcgencmd get_throttled 2>/dev/null || true
    printf '\nDevice-tree overlays:\n'
    dtoverlay -l 2>/dev/null || true
    printf '\nEEPROM status:\n'
    rpi-eeprom-update 2>/dev/null || true
    printf '\nRaspberry Pi configuration files captured:\n'
    find /boot /boot/firmware /etc -maxdepth 2 -type f \( \
        -path '*/config.txt' -o -path '*/cmdline.txt' -o -path '*/usercfg.txt' -o \
        -path '*/sysconf.txt' -o -path '/etc/dhcpcd.conf' -o -path '/etc/modules' -o \
        -path '/etc/fstab' -o -path '/etc/modprobe.d/*' -o -path '/etc/udev/rules.d/*' \
    \) -print 2>/dev/null | sort
} > "${WORK_DIR}/metadata/raspberry-pi-configuration.txt"

cat > "${WORK_DIR}/README-RESTORE.md" <<'EOF'
# TouchPlayer Backup Restore

This archive contains the TouchPlayer source and deployed copy, system
configuration, cellular PPP files, kiosk autostart files, MPD/Samba/Bluetooth
state, application cache/database files, package inventories, and checksums.
Raspberry Pi boot and hardware configuration is always stored separately under
the raspberry-pi/ directory. It is only applied during restore when
--include-pi-config is explicitly passed to restore.sh.

The archive may contain Wi-Fi, Samba, PPP, or SMS configuration. Keep it
private.

## Restore on a replacement Raspberry Pi

1. Install Raspberry Pi OS and create the normal `pi` user.
2. Copy this archive and its `.sha256` file to the new Pi.
3. Verify the archive:

   ```sh
   sha256sum -c touchplayer-backup-*.tar.gz.sha256
   ```

4. Extract it to a temporary directory:

   ```sh
   mkdir -p /tmp/touchplayer-restore
   sudo tar -xzf touchplayer-backup-*.tar.gz -C /tmp/touchplayer-restore
   ```

5. Restore files and configuration:

   ```sh
   sudo /tmp/touchplayer-restore/restore.sh
   ```

    To explicitly restore the Raspberry Pi boot, UART, and hardware
    configuration from a backup that contains it, use:

    ```sh
    sudo /tmp/touchplayer-restore/restore.sh --include-pi-config
    ```

6. Install dependencies and rebuild generated environments:

   ```sh
   sudo bash /opt/touchplayer/install/install.sh
   ```

7. Reboot the Pi and verify the kiosk, MPD, network, and cellular services.

The install script recreates the Python virtual environment, Node modules,
frontend build, and other generated files that are intentionally not stored
in the archive. Use `--include-media` when creating the backup if the music
library must also be restored.
EOF

cat > "${WORK_DIR}/restore.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

INCLUDE_PI_CONFIG=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --include-pi-config)
            INCLUDE_PI_CONFIG=true
            shift
            ;;
        -h|--help)
            echo "Usage: sudo $0 [--include-pi-config]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: sudo $0 [--include-pi-config]" >&2
            exit 2
            ;;
    esac
done

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run restore.sh with sudo." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/root"
[[ -d "${ROOT_DIR}" ]] || { echo "Backup root is missing: ${ROOT_DIR}" >&2; exit 1; }

cp -a "${ROOT_DIR}/." /

if [[ "${INCLUDE_PI_CONFIG}" == true ]]; then
    PI_ROOT_DIR="${SCRIPT_DIR}/raspberry-pi"
    if [[ -d "${PI_ROOT_DIR}" ]]; then
        cp -a "${PI_ROOT_DIR}/." /
        echo "Raspberry Pi boot and hardware configuration restored."
    else
        echo "No Raspberry Pi configuration is stored in this backup." >&2
        exit 1
    fi
fi

if [[ -f /etc/sudoers.d/touchplayer-sms ]]; then
    visudo -cf /etc/sudoers.d/touchplayer-sms
fi

mkdir -p /etc/systemd/system/mpd.service.d
chown -R pi:pi /opt/touchplayer /home/pi/Development/TouchPlayer 2>/dev/null || true
chmod 440 /etc/sudoers.d/touchplayer-sms 2>/dev/null || true
chmod 600 /etc/ppp/peers/touchplayer-cellular /etc/chatscripts/touchplayer-cellular 2>/dev/null || true
systemctl daemon-reload
nginx -t

echo "TouchPlayer files and configuration restored."
echo "Run: sudo bash /opt/touchplayer/install/install.sh"
EOF
chmod 755 "${WORK_DIR}/restore.sh"

(
    cd "${WORK_DIR}"
    find root raspberry-pi -type f -print0 | sort -z | xargs -0 sha256sum > checksums.sha256
)

# Archive relative paths so it can be extracted on any replacement Pi.
tar -C "${WORK_DIR}" -czf "${ARCHIVE_PATH}" .
chmod 600 "${ARCHIVE_PATH}"
sha256sum "${ARCHIVE_PATH}" > "${ARCHIVE_PATH}.sha256"

if [[ -n "${BACKUP_OWNER_UID}" && -n "${BACKUP_OWNER_GID}" ]]; then
    chown "${BACKUP_OWNER_UID}:${BACKUP_OWNER_GID}" "${ARCHIVE_PATH}" "${ARCHIVE_PATH}.sha256"
fi

printf '\nTouchPlayer backup created:\n  %s\n  %s\n' "${ARCHIVE_PATH}" "${ARCHIVE_PATH}.sha256"
printf 'Archive size: %s\n' "$(du -h "${ARCHIVE_PATH}" | awk '{print $1}')"
printf 'Restore instructions are included as README-RESTORE.md inside the archive.\n'
