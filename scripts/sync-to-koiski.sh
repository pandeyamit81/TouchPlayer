#!/usr/bin/env bash
# Sync the working tree to the KOISKI installation and restart TouchPlayer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${KOISKI_DIR:-/opt/touchplayer}"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run]

Sync the current TouchPlayer checkout to ${TARGET_DIR}, build the frontend,
and restart the backend services. Set KOISKI_DIR to override the install path.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "KOISKI install directory does not exist: ${TARGET_DIR}" >&2
    exit 1
fi

RSYNC_ARGS=(
    --archive
    --delete
    --human-readable
    --chown=pi:pi
    --no-owner
    --no-group
    --exclude '.git/'
    --exclude 'venv/'
    --exclude 'frontend/node_modules/'
    --exclude 'frontend/dist/'
    --exclude 'cache/'
    --exclude 'data/'
    --exclude '__pycache__/'
    --exclude '*.pyc'
)

if [[ "${DRY_RUN}" == true ]]; then
    RSYNC_ARGS+=(--dry-run)
fi

echo "Syncing ${SCRIPT_DIR} -> ${TARGET_DIR}"
sudo rsync "${RSYNC_ARGS[@]}" "${SCRIPT_DIR}/" "${TARGET_DIR}/"

if [[ "${DRY_RUN}" == true ]]; then
    echo "Dry run complete; no services were changed."
    exit 0
fi

echo "Repairing frontend ownership..."
sudo chown -R pi:pi "${TARGET_DIR}/frontend"

echo "Updating Python dependencies..."
source "${TARGET_DIR}/venv/bin/activate"
python -m pip install -r "${TARGET_DIR}/backend/requirements.txt" --upgrade

echo "Building frontend..."
cd "${TARGET_DIR}/frontend"
npm install
npm run build

echo "Installing service and system configuration..."
sudo install -m 644 "${TARGET_DIR}/systemd/"*.service /etc/systemd/system/
sudo install -m 644 "${TARGET_DIR}/systemd/mpd.service.d/pipewire.conf" /etc/systemd/system/mpd.service.d/pipewire.conf
sudo install -m 644 "${TARGET_DIR}/configs/mpd/mpd.conf" /etc/mpd.conf
sudo install -m 644 "${TARGET_DIR}/configs/nginx/touchplayer.conf" /etc/nginx/sites-available/touchplayer
sudo install -D -m 440 "${TARGET_DIR}/configs/sudoers.d/touchplayer-sms" /etc/sudoers.d/touchplayer-sms
sudo visudo -cf /etc/sudoers.d/touchplayer-sms
sudo chown -R pi:pi /var/lib/mpd /var/log/mpd

echo "Restarting TouchPlayer..."
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl restart mpd nginx
sudo systemctl restart touchplayer-api touchplayer-mpd-listener touchplayer-bluetooth
sudo systemctl start touchplayer-indexer

echo "KOISKI sync complete."