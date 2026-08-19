#!/bin/bash
# TouchPlayer Bluetooth Manager
# Manages Bluetooth device connections

set -e

echo "=== TouchPlayer Bluetooth Manager ==="

# Activate virtual environment
source /opt/touchplayer/venv/bin/activate

# Run the Bluetooth manager
cd /opt/touchplayer/backend
python -m app.services.bluetooth.manager

echo "=== Bluetooth Manager Running ==="
