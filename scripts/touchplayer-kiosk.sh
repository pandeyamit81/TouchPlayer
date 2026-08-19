#!/bin/sh

set -u

URL="http://localhost/"
CHROMIUM_BIN="$(command -v chromium-browser || command -v chromium || true)"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

DISPLAY_ARGS=""
find_graphical_session() {
    if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
        DISPLAY_ARGS="--ozone-platform=wayland"
        return 0
    fi

    if [ -z "${WAYLAND_DISPLAY:-}" ]; then
        for wayland_socket in "$XDG_RUNTIME_DIR"/wayland-*; do
            if [ -S "$wayland_socket" ]; then
                WAYLAND_DISPLAY="${wayland_socket##*/}"
                export WAYLAND_DISPLAY
                DISPLAY_ARGS="--ozone-platform=wayland"
                return 0
            fi
        done
    fi

    if [ -n "${DISPLAY:-}" ]; then
        return 0
    fi

    if [ -S /tmp/.X11-unix/X0 ]; then
        DISPLAY=:0
        export DISPLAY
        return 0
    fi

    return 1
}

if [ -z "$CHROMIUM_BIN" ]; then
    exit 0
fi

# Wait for the graphical session and local web server before opening Chromium.
while ! find_graphical_session; do
    sleep 2
done

while ! curl -fsS --max-time 2 "$URL" >/dev/null 2>&1; do
    sleep 2
done

while true; do
    "$CHROMIUM_BIN" \
        --kiosk \
        --start-fullscreen \
        $DISPLAY_ARGS \
        --app="$URL" \
        --incognito \
        --no-first-run \
        --no-default-browser-check \
        --window-size=800,480 \
        --force-device-scale-factor=1 \
        --noerrdialogs \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-http-cache \
        --disk-cache-size=1 \
        --disable-pinch \
        --overscroll-history-navigation=0 \
        --password-store=basic
    sleep 2
done
