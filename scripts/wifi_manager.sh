#!/bin/bash
# TouchPlayer WiFi Manager
# Manages WiFi network connections

set -e

echo "=== TouchPlayer WiFi Manager ==="

# Activate virtual environment
source /opt/touchplayer/venv/bin/activate

# Run the WiFi manager
cd /opt/touchplayer/backend
python -m app.services.wifi.manager

echo "=== WiFi Manager Running ==="
