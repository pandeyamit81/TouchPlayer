#!/bin/bash
# TouchPlayer Media Library Scanner
# Scans media files and updates the database

set -e

echo "=== TouchPlayer Media Library Scanner ==="

# Activate virtual environment
source /opt/touchplayer/venv/bin/activate

# Run the scanner
cd /opt/touchplayer/backend
python -m app.services.library.scanner

echo "=== Scan Complete ==="
