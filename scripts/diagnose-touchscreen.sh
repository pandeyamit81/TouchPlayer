#!/bin/bash
# Diagnose Raspberry Pi touchscreen/display mapping for TouchPlayer.
# This script is read-only unless --install-session-fix is supplied.

set -u

CONFIG_FILE="/boot/firmware/config.txt"
REPORT_ONLY=1
TARGET_USER="${SUDO_USER:-$(id -un)}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

if [[ "${1:-}" == "--install-session-fix" ]]; then
    REPORT_ONLY=0
fi

printf '%s\n' '=== TouchPlayer Touchscreen Diagnostic ==='
printf 'Kernel: '
printf '%s\n' "$(uname -r)"
printf 'Desktop: '
printf '%s\n' "${XDG_SESSION_DESKTOP:-unknown} (${XDG_SESSION_TYPE:-unknown})"
printf 'Desktop user: '
printf '%s\n' "$TARGET_USER"
printf '\n--- Boot overlays ---\n'
if [[ -r "$CONFIG_FILE" ]]; then
    grep -nE 'dtoverlay|display_auto_detect|dsi|hdmi|spi|ads7846|fbcon' "$CONFIG_FILE" || true
else
    printf 'Cannot read %s\n' "$CONFIG_FILE"
fi

printf '\n--- DRM connectors ---\n'
DSI_CONNECTED=0
for status_file in /sys/class/drm/*/status; do
    [[ -r "$status_file" ]] || continue
    connector="${status_file%/status}"
    status="$(cat "$status_file")"
    printf '%s: %s' "${connector##*/}" "$status"
    if [[ -r "$connector/modes" ]]; then
        printf '  mode='
        head -n 1 "$connector/modes"
    else
        printf '\n'
    fi
    if [[ "${connector##*/}" == *DSI* && "$status" == connected ]]; then
        DSI_CONNECTED=1
    fi
done

printf '\n--- Framebuffers ---\n'
for framebuffer in /sys/class/graphics/fb*; do
    [[ -d "$framebuffer" ]] || continue
    printf '%s: ' "$framebuffer"
    cat "$framebuffer/name" 2>/dev/null || printf 'unknown'
    printf '  size='
    cat "$framebuffer/virtual_size" 2>/dev/null || printf 'unknown'
    printf '\n'
done

printf '\n--- Touch input ---\n'
TOUCH_FOUND=0
for name_file in /sys/class/input/event*/device/name; do
    [[ -r "$name_file" ]] || continue
    device_name="$(cat "$name_file")"
    if printf '%s' "$device_name" | grep -qiE 'touch|ft5|goodix|egalax|ads7846'; then
        event_name="${name_file#/sys/class/input/}"
        event_name="${event_name%%/*}"
        touch_device="/dev/input/${event_name}"
        printf '%s (%s)\n' "$device_name" "$touch_device"
        udevadm info --query=property --name="$touch_device" 2>/dev/null | grep -E 'DEVNAME|ID_INPUT|ID_PATH|LIBINPUT' || true
        stat -c 'Device permissions: %A %U:%G %n' "$touch_device"
        TOUCH_FOUND=1
    fi
done
if (( ! TOUCH_FOUND )); then
    printf 'No touchscreen input device was found.\n'
fi
if id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx input; then
    printf '%s input-group access: yes\n' "$TARGET_USER"
else
    printf '%s input-group access: no\n' "$TARGET_USER"
fi

printf '\n--- Compositor ---\n'
pgrep -af 'labwc|wayfire|weston|Xorg|lightdm' || true

printf '\n--- Diagnosis ---\n'
if (( DSI_CONNECTED )); then
    printf '%s\n' 'A DSI display is connected through DRM/KMS.'
else
    printf '%s\n' 'No connected DSI display was detected.'
fi
if [[ -r "$CONFIG_FILE" ]] && grep -qE '^[[:space:]]*dtoverlay=ads7846([,[:space:]]|$)' "$CONFIG_FILE"; then
    printf '%s\n' 'The legacy ADS7846 SPI touch overlay is still enabled.'
    printf '%s\n' 'Remove it and run scripts/configure-dsi-touch.sh, then reboot.'
elif (( TOUCH_FOUND )); then
    printf '%s\n' 'A touch controller is visible to the input stack.'
else
    printf '%s\n' 'No touch controller is visible to the input stack. Check the DSI touch cable and kernel logs.'
fi

if (( REPORT_ONLY )); then
    printf '\n%s\n' 'No changes were made.'
    printf '%s\n' 'Run with --install-session-fix only to install the safe input-session checks.'
    exit 0
fi

printf '\n--- Installing safe session fix ---\n'
if [[ "$(id -u)" -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Ensure the desktop user can read input devices. This does not change boot overlays.
if id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx input; then
    printf '%s\n' 'Desktop user already belongs to the input group.'
else
    $SUDO usermod -aG input "$TARGET_USER"
    printf '%s\n' "Added ${TARGET_USER} to the input group."
fi

# Back up the current labwc session configuration before writing anything.
LABWC_DIR="${TARGET_HOME}/.config/labwc"
LABWC_AUTOSTART="${LABWC_DIR}/autostart"
if [[ -f "$LABWC_AUTOSTART" ]]; then
    cp "$LABWC_AUTOSTART" "${LABWC_AUTOSTART}.touchplayer-backup.$(date +%Y%m%d%H%M%S)"
fi
mkdir -p "$LABWC_DIR"

# Keep the existing kiosk startup in the active labwc session.
if [[ ! -f "$LABWC_AUTOSTART" ]]; then
    printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' > "$LABWC_AUTOSTART"
elif ! grep -Fqx '/usr/local/bin/touchplayer-kiosk &' "$LABWC_AUTOSTART"; then
    printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' >> "$LABWC_AUTOSTART"
fi
chmod 755 "$LABWC_AUTOSTART"

printf '%s\n' 'Session fix installed. Log out/in or reboot for group membership to refresh.'
printf '%s\n' 'For DSI panels, run scripts/configure-dsi-touch.sh before rebooting if the legacy SPI overlay is present.'
