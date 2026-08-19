#!/bin/bash
# TouchPlayer Installation Script
# This script installs all dependencies and sets up TouchPlayer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/touchplayer"

if [[ "$(id -u)" -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

echo "=== TouchPlayer Installation ==="

# Check if running on Raspberry Pi
if [ ! -f "/etc/rpi-issue" ]; then
    echo "Warning: This script is designed for Raspberry Pi"
fi

# Update system
echo "Updating system packages..."
$SUDO apt-get update

# Install dependencies
echo "Installing dependencies..."

# System dependencies
sudo apt-get install -y \
    build-essential \
    cmake \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    mpd \
    ffmpeg \
    alsa-utils \
    bluez \
    bluez-tools \
    modemmanager \
    libqmi-utils \
    libmbim-utils \
    ppp \
    usb-modeswitch \
    usb-modeswitch-data \
    pipewire \
    pipewire-pulse \
    wireplumber \
    libspa-0.2-bluetooth \
    network-manager \
    python3-rpi.gpio \
    nginx \
    samba \
    curl \
    git

echo "Staging source at ${INSTALL_DIR}..."
if [[ "${SCRIPT_DIR}" != "${INSTALL_DIR}" ]]; then
    $SUDO mkdir -p "${INSTALL_DIR}"
    $SUDO cp -a "${SCRIPT_DIR}/." "${INSTALL_DIR}/"
fi
$SUDO rm -rf "${INSTALL_DIR}/venv"
$SUDO chown -R pi:pi "${INSTALL_DIR}"

# Install the local Whisper runtime and tiny English model used by track transcription.
$SUDO bash "${INSTALL_DIR}/scripts/install-whisper.sh"

# Python dependencies
echo "Installing Python dependencies..."
python3 -m venv "${INSTALL_DIR}/venv"
source "${INSTALL_DIR}/venv/bin/activate"

pip install --upgrade pip
pip install -r "${INSTALL_DIR}/backend/requirements.txt"

# Install Node.js and dependencies
echo "Installing Node.js dependencies..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

cd "${INSTALL_DIR}/frontend"
npm install
npm run build

# Create directories
echo "Creating directories..."
$SUDO mkdir -p "${INSTALL_DIR}/data" "${INSTALL_DIR}/cache/artwork" "${INSTALL_DIR}/cache/thumbnails"
$SUDO mkdir -p /home/pi/Music /media
$SUDO chown -R pi:pi "${INSTALL_DIR}" /home/pi/Music /media

# Copy systemd services
echo "Installing systemd services..."
$SUDO cp "${INSTALL_DIR}/systemd/"*.service /etc/systemd/system/
$SUDO install -D -m 440 "${INSTALL_DIR}/configs/sudoers.d/touchplayer-sms" /etc/sudoers.d/touchplayer-sms
$SUDO visudo -cf /etc/sudoers.d/touchplayer-sms
$SUDO mkdir -p /etc/systemd/system/mpd.service.d
$SUDO cp "${INSTALL_DIR}/systemd/mpd.service.d/pipewire.conf" /etc/systemd/system/mpd.service.d/pipewire.conf

# Copy nginx configuration
echo "Installing nginx configuration..."
$SUDO cp "${INSTALL_DIR}/configs/nginx/touchplayer.conf" /etc/nginx/sites-available/touchplayer
$SUDO ln -sf /etc/nginx/sites-available/touchplayer /etc/nginx/sites-enabled/touchplayer
$SUDO rm -f /etc/nginx/sites-enabled/default
$SUDO nginx -t
$SUDO systemctl reload nginx || $SUDO systemctl restart nginx

# Enable and start services
echo "Enabling services..."
$SUDO systemctl daemon-reload
$SUDO systemctl enable mpd nginx bluetooth
$SUDO systemctl enable touchplayer-api touchplayer-indexer touchplayer-mpd-listener touchplayer-bluetooth

# Start services
echo "Starting services..."
$SUDO systemctl restart mpd
$SUDO systemctl enable --now nginx bluetooth
$SUDO systemctl start touchplayer-api touchplayer-mpd-listener touchplayer-indexer touchplayer-bluetooth

# Configure MPD
echo "Configuring MPD..."
$SUDO cp "${INSTALL_DIR}/configs/mpd/mpd.conf" /etc/mpd.conf
$SUDO chown -R pi:pi /var/lib/mpd /var/log/mpd
$SUDO systemctl restart mpd

# Configure Samba (standalone file server; the 'samba' package also pulls in
# samba-ad-dc, which is disabled since a domain controller is not needed here)
echo "Configuring Samba file sharing..."
$SUDO systemctl disable --now samba-ad-dc 2>/dev/null || true
$SUDO systemctl mask samba-ad-dc 2>/dev/null || true
$SUDO mkdir -p /etc/samba/smb.conf.d
if [[ ! -f /etc/samba/smb.conf.d/touchplayer.conf ]]; then
    printf '# Managed by TouchPlayer -- edited via Settings > Network Share\n' | $SUDO tee /etc/samba/smb.conf.d/touchplayer.conf >/dev/null
    $SUDO chmod 644 /etc/samba/smb.conf.d/touchplayer.conf
fi
if ! $SUDO grep -q 'smb.conf.d/touchplayer.conf' /etc/samba/smb.conf; then
    printf '\ninclude = /etc/samba/smb.conf.d/touchplayer.conf\n' | $SUDO tee -a /etc/samba/smb.conf >/dev/null
fi
$SUDO systemctl enable --now smbd nmbd

# Configure Chromium kiosk
echo "Configuring Chromium kiosk..."
$SUDO install -m 755 -o pi -g pi "${INSTALL_DIR}/scripts/touchplayer-kiosk.sh" /usr/local/bin/touchplayer-kiosk
$SUDO mkdir -p /home/pi/.config/labwc
printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' | $SUDO tee /home/pi/.config/labwc/autostart >/dev/null
$SUDO chown pi:pi /home/pi/.config/labwc/autostart

# Keep an LXDE fallback for Raspberry Pi images that use the legacy session.
$SUDO chmod 755 /home/pi/.config/labwc/autostart
$SUDO mkdir -p /etc/xdg/lxsession/LXDE-pi
CHROMIUM_BIN="$(command -v chromium-browser || command -v chromium || true)"
if [[ -n "${CHROMIUM_BIN}" ]]; then
cat << EOF | $SUDO tee /etc/xdg/lxsession/LXDE-pi/autostart
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@/usr/local/bin/touchplayer-kiosk
EOF
else
    echo "Chromium not found; skipping kiosk autostart configuration."
fi

echo "=== Installation Complete ==="
echo "TouchPlayer is now installed and running!"
echo "Access the web interface at http://localhost"
echo ""
echo "Useful commands:"
echo "  - systemctl status touchplayer-api"
echo "  - systemctl status touchplayer-mpd-listener"
echo "  - journalctl -u touchplayer-api -f"
echo "  - journalctl -u touchplayer-mpd-listener -f"
