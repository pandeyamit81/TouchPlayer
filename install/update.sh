#!/bin/bash
# TouchPlayer Update Script
# This script updates TouchPlayer to the latest version

set -e

echo "=== TouchPlayer Update ==="

# Stop services
echo "Stopping services..."
sudo systemctl stop touchplayer-indexer touchplayer-mpd-listener touchplayer-api touchplayer-bluetooth || true

echo "Installing modem support..."
sudo apt-get install -y modemmanager libqmi-utils libmbim-utils ppp usb-modeswitch usb-modeswitch-data python3-rpi.gpio

# Pull latest changes
echo "Pulling latest changes..."
cd /opt/touchplayer
git pull origin main

sudo cp systemd/*.service /etc/systemd/system/
sudo install -D -m 440 configs/sudoers.d/touchplayer-sms /etc/sudoers.d/touchplayer-sms
sudo visudo -cf /etc/sudoers.d/touchplayer-sms
sudo install -m 755 -o pi -g pi scripts/touchplayer-kiosk.sh /usr/local/bin/touchplayer-kiosk
sudo mkdir -p /home/pi/.config/labwc
printf '%s\n' '/usr/local/bin/touchplayer-kiosk &' | sudo tee /home/pi/.config/labwc/autostart >/dev/null
sudo chown pi:pi /home/pi/.config/labwc/autostart
sudo chmod 755 /home/pi/.config/labwc/autostart

sudo mkdir -p /etc/xdg/lxsession/LXDE-pi
cat << 'EOF' | sudo tee /etc/xdg/lxsession/LXDE-pi/autostart >/dev/null
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@/usr/local/bin/touchplayer-kiosk
EOF
sudo mkdir -p /etc/systemd/system/mpd.service.d
sudo cp systemd/mpd.service.d/pipewire.conf /etc/systemd/system/mpd.service.d/pipewire.conf
sudo cp configs/mpd/mpd.conf /etc/mpd.conf
sudo chown -R pi:pi /var/lib/mpd /var/log/mpd
sudo cp configs/nginx/touchplayer.conf /etc/nginx/sites-available/touchplayer

# Keep the local Whisper runtime and model available after updates.
sudo bash /opt/touchplayer/scripts/install-whisper.sh

# Update Python dependencies
echo "Updating Python dependencies..."
source /opt/touchplayer/venv/bin/activate
pip install -r /opt/touchplayer/backend/requirements.txt --upgrade

# Update Node.js dependencies
echo "Updating Node.js dependencies..."
cd /opt/touchplayer/frontend
npm install
npm run build

# Reload and restart services
echo "Restarting services..."
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable mpd nginx bluetooth smbd nmbd touchplayer-api touchplayer-indexer touchplayer-mpd-listener touchplayer-bluetooth
sudo systemctl restart mpd nginx bluetooth smbd nmbd
sudo systemctl start touchplayer-api touchplayer-mpd-listener touchplayer-indexer touchplayer-bluetooth

echo "=== Update Complete ==="
