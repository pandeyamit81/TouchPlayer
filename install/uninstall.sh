#!/bin/bash
# TouchPlayer Uninstall Script
# This script removes TouchPlayer from the system

set -e

echo "=== TouchPlayer Uninstall ==="

# Stop services
echo "Stopping services..."
sudo systemctl stop touchplayer-api
sudo systemctl stop touchplayer-mpd-listener
sudo systemctl stop touchplayer-indexer

# Disable services
echo "Disabling services..."
sudo systemctl disable touchplayer-api
sudo systemctl disable touchplayer-mpd-listener
sudo systemctl disable touchplayer-indexer
sudo systemctl disable touchplayer-bluetooth
sudo systemctl disable mpd nginx bluetooth
sudo systemctl disable smbd nmbd

# Remove systemd services
echo "Removing systemd services..."
sudo rm -f /etc/systemd/system/touchplayer-*.service
sudo rm -f /etc/systemd/system/mpd.service.d/pipewire.conf
sudo rm -f /usr/local/bin/touchplayer-kiosk
sudo rm -f /home/pi/.config/labwc/autostart
sudo systemctl daemon-reload

# Remove nginx configuration
echo "Removing nginx configuration..."
sudo rm -f /etc/nginx/sites-enabled/touchplayer
sudo rm -f /etc/nginx/sites-available/touchplayer

# Remove Python environment
echo "Removing Python environment..."
sudo rm -rf /opt/touchplayer/venv

# Remove frontend build
echo "Removing frontend build..."
sudo rm -rf /opt/touchplayer/frontend/dist

# Remove data and cache
echo "Removing data and cache..."
sudo rm -rf /opt/touchplayer/data
sudo rm -rf /opt/touchplayer/cache

# Remove source code
echo "Removing source code..."
sudo rm -rf /opt/touchplayer

# Remove nginx site
sudo systemctl restart nginx

echo "=== Uninstall Complete ==="
echo "TouchPlayer has been removed from your system."
