## Disaster Recovery Backup

Create a private, checksummed archive containing the source tree, deployed
copy, system configuration, cellular PPP files, kiosk settings, MPD/Samba/
Bluetooth state, Raspberry Pi boot/UART/hardware configuration, application
data, and restore instructions:

```bash
sudo scripts/backup-touchplayer.sh --destination /media/pi/TOUCHPLAYER_BACKUP
```

Raspberry Pi configuration is backed up every time under the archive's
`raspberry-pi/` directory. It is not restored by default. To apply it on a
replacement Pi, explicitly pass `--include-pi-config` to the restore helper:

```bash
sha256sum -c touchplayer-backup-*.tar.gz.sha256
mkdir -p /tmp/touchplayer-restore
sudo tar -xzf touchplayer-backup-*.tar.gz -C /tmp/touchplayer-restore
sudo /tmp/touchplayer-restore/restore.sh --include-pi-config
sudo bash /opt/touchplayer/install/install.sh
```

Use `--include-media` when the music library under `/home/pi/Music` should be
included. The generated archive is readable by the invoking `pi` user and is
protected with mode `600`.
# TouchPlayer

A complete Raspberry Pi touchscreen media player operating system with a modern UI, similar to Volumio, Moode Audio, and piCorePlayer.

## Features

- **Media Library**: Scan and organize your music collection
- **Playback Control**: Full MPD integration with play, pause, stop, seek, volume control
- **Queue Management**: Add, remove, reorder tracks in the playback queue
- **Playlist Management**: Create and manage playlists
- **Album Artwork**: Automatic artwork extraction and caching
- **Bluetooth**: Connect to Bluetooth speakers
- **WiFi**: Connect to WiFi networks
- **Modern UI**: Material Design 3 with touch-friendly interface
- **Local-First**: SQLite database with FTS5 search
- **Real-time Updates**: WebSocket-based live updates

## Hardware Requirements

- Raspberry Pi 4 (4GB or 8GB recommended)
- Raspberry Pi OS Bookworm (64-bit)
- 4.3-inch 800x480 DSI touchscreen (or external monitor)
- USB SSD (recommended for better performance)
- Bluetooth speakers (optional)
- SIM868 GSM/GPRS module and an activated SIM (optional)
- WiFi or Ethernet connection

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/touchplayer.git
cd touchplayer

# Run the installation script
sudo bash install/install.sh
```

The installer stages the application at `/opt/touchplayer`, builds the frontend,
configures MPD and PipeWire, and enables TouchPlayer, MPD, Nginx, Bluetooth,
the media indexer, and the MPD event listener to start automatically at boot.

### Manual Install

1. Install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-venv python3-pip \
    mpd ffmpeg alsa-utils bluez network-manager nginx git
```

2. Set up Python environment:
```bash
python3 -m venv /opt/touchplayer/venv
source /opt/touchplayer/venv/bin/activate
pip install -r backend/requirements.txt
```

3. Set up frontend:
```bash
cd frontend
npm install
npm run build
```

4. Install systemd services and the MPD PipeWire drop-in:
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/mpd.service.d
sudo cp systemd/mpd.service.d/pipewire.conf /etc/systemd/system/mpd.service.d/
sudo systemctl daemon-reload
sudo systemctl enable mpd nginx bluetooth
sudo systemctl enable touchplayer-api touchplayer-mpd-listener touchplayer-indexer touchplayer-bluetooth
```

5. Configure nginx:
```bash
sudo cp configs/nginx/touchplayer.conf /etc/nginx/sites-available/touchplayer
sudo ln -sf /etc/nginx/sites-available/touchplayer /etc/nginx/sites-enabled/touchplayer
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

6. Start services:
```bash
sudo systemctl enable --now mpd nginx bluetooth
sudo systemctl start touchplayer-api touchplayer-mpd-listener touchplayer-indexer touchplayer-bluetooth
```

## Usage

1. Access the web interface at `http://localhost`
2. The interface will automatically launch in kiosk mode on boot
3. Use the navigation menu to access different features:
   - **Home**: Quick access to all features
   - **Library**: Browse your music collection
   - **Albums**: View and play albums
   - **Artists**: View and play artists
   - **Playlists**: Manage playlists
   - **Bluetooth**: Connect to Bluetooth devices
   - **WiFi**: Connect to WiFi networks
   - **Settings**: Configure TouchPlayer

To control the kiosk browser without restarting TouchPlayer services:

```bash
bash scripts/restart-touchplayer-kiosk.sh restart
bash scripts/restart-touchplayer-kiosk.sh stop
bash scripts/restart-touchplayer-kiosk.sh start
```

Track transcription uses local `whisper.cpp` with the `tiny.en` model. Fresh
installs and updates build `whisper-cli` and download the model automatically.
To install or repair it manually:

```bash
sudo bash scripts/install-whisper.sh
```

### Configure the SIM868 Cellular Module

The SIM868 must have suitable external power, a SIM with mobile data enabled, and its
GPIO header seated correctly on the Pi. This board communicates through the
Pi's UART pins rather than appearing as a USB modem. Configure it with the APN
supplied by the mobile carrier:

```bash
sudo bash scripts/configure-cellular.sh --apn YOUR_CARRIER_APN
```

The script installs modem support, enables the GPIO UART, removes the serial
boot console, creates a PPP dial-up service for `/dev/serial0`, and enables
autoconnect after reboot. The Pi 5 UART overlay is applied only on Pi 5; Pi 4
uses its standard GPIO14/GPIO15 UART mapping. For USB modem variants it uses
ModemManager and NetworkManager instead. For carriers requiring credentials:

```bash
sudo env TOUCHPLAYER_CELLULAR_USERNAME=USER \
    TOUCHPLAYER_CELLULAR_PASSWORD=PASSWORD \
    bash scripts/configure-cellular.sh --apn YOUR_CARRIER_APN
```

Check modem registration and the active data connection with:

```bash
bash scripts/diagnose-cellular.sh
```

The PPP service waits for packet attachment before dialing. If the SIM868
reports `CSQ: 0,0`, `CREG: 0,2`, or `CGATT: 0`, check antenna placement,
network coverage, SIM activation, and the carrier APN before retrying.

The Waveshare SIM868 PWRKEY input is wired to physical header pin 7 (BCM GPIO4).
The SMS network restart action stops PPP, drives PWRKEY low for four seconds,
waits for the modem to boot, and then starts PPP again.

If the SIM868 is powered but no modem is listed, run the configuration command:
it will install the UART PPP path automatically. Reboot afterward, then check
`/dev/serial0`, the `touchplayer-cellular` service, and registration with the
diagnostic command.

### Sync Development Changes to KOISKI

When working from this checkout, sync uncommitted backend or frontend changes
to the installed kiosk with:

```bash
bash scripts/sync-to-koiski.sh
```

The script preserves the installed virtual environment, frontend dependencies,
database, and cache. Use `--dry-run` to review files before syncing, or set
`KOISKI_DIR` when the kiosk installation is not at `/opt/touchplayer`.

Bluetooth devices connected from the Bluetooth page are trusted and remembered
for automatic reconnection. The Bluetooth service retries remembered devices
when BlueZ starts after a reboot or shutdown. On the first deployment of this
feature, a device that is already connected is enrolled automatically.

### Configure the 4.3-inch DSI Display

On a Raspberry Pi that previously used the 3.5-inch SPI/TinyLCD panel, remove
the old framebuffer and `ADS7846` overlay before starting the DSI kiosk:

```bash
sudo bash scripts/configure-dsi-touch.sh
sudo reboot
```

The script preserves the DRM/KMS session, enables DSI display auto-detection,
removes the legacy SPI touch overlay, keeps the DSI panel at its native mode
(`800x480`), and installs the kiosk launcher for the Pi desktop session. The
old `scripts/configure-tinylcd-touch.sh` path remains as a compatibility
wrapper. After reboot, inspect the active display and touch controller with:

```bash
bash scripts/diagnose-touchscreen.sh
```

Metadata enrichment uses MusicBrainz, an open and free metadata service. It
requires no API key. Requests are rate-limited and use a descriptive User-Agent.

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
touchplayer/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── database/     # Database models and session
│   │   ├── models/       # Pydantic models
│   │   ├── routes/       # API routes
│   │   ├── services/     # Business logic
│   │   ├── websocket/    # WebSocket manager
│   │   └── main.py       # FastAPI app
│   └── requirements.txt  # Python dependencies
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── store/        # Zustand store
│   │   └── main.tsx      # React app entry
│   └── package.json      # Node.js dependencies
├── systemd/              # Systemd service files
├── configs/              # Configuration files
│   ├── nginx/            # Nginx configuration
│   └── mpd/              # MPD configuration
├── install/              # Installation scripts
├── docs/                 # Documentation
├── tests/                # Test files
└── README.md             # This file
```

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy 2.x**: ORM for SQLite
- **Alembic**: Database migrations
- **python-mpd2**: MPD client library
- **Loguru**: Logging
- **Watchdog**: File system monitoring

### Frontend
- **React**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **Material UI**: UI components
- **Zustand**: State management
- **React Query**: Data fetching

### Database
- **SQLite**: Local database
- **FTS5**: Full-text search

### System
- **systemd**: Service management
- **Nginx**: Web server and reverse proxy
- **MPD**: Music Player Daemon
- **BlueZ**: Bluetooth stack
- **PipeWire/WirePlumber**: Audio routing to HDMI, analog, and Bluetooth sinks

## Development

### Backend Development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Volumio, Moode Audio, and piCorePlayer
- Uses MPD for audio playback
- Built with Raspberry Pi community in mind

## Support

For support, please open an issue on GitHub or join our Discord server.
