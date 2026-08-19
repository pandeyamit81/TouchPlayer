#!/bin/sh

set -eu

KIOSK_LAUNCHER="${KIOSK_LAUNCHER:-/usr/local/bin/touchplayer-kiosk}"
KIOSK_USER="${KIOSK_USER:-$(id -un)}"
ACTION="${1:-restart}"

case "$ACTION" in
    start|stop|restart)
        ;;
    -h|--help)
        echo "Usage: $0 [start|stop|restart]"
        exit 0
        ;;
    *)
        echo "Usage: $0 [start|stop|restart]" >&2
        exit 2
        ;;
esac

# The launcher supervises Chromium and starts it again after it exits.
if [ "$ACTION" = stop ] || [ "$ACTION" = restart ]; then
    pkill -TERM -u "$KIOSK_USER" -f '(^|/)(chromium|chromium-browser)( |$).*--kiosk' 2>/dev/null || true
fi

if [ "$ACTION" = stop ]; then
    pkill -TERM -u "$KIOSK_USER" -f '(^|/)touchplayer-kiosk( |$)' 2>/dev/null || true
    echo "TouchPlayer kiosk stopped."
    exit 0
fi

if [ ! -x "$KIOSK_LAUNCHER" ]; then
    echo "Kiosk launcher not found or not executable: $KIOSK_LAUNCHER" >&2
    exit 1
fi

if ! pgrep -u "$KIOSK_USER" -f '(^|/)touchplayer-kiosk( |$)' >/dev/null 2>&1; then
    nohup "$KIOSK_LAUNCHER" >/tmp/touchplayer-kiosk.log 2>&1 &
fi

echo "TouchPlayer kiosk $ACTION requested."
