# TouchPlayer Documentation

## Overview

TouchPlayer is a complete Raspberry Pi touchscreen media player operating system with a modern UI, similar to Volumio, Moode Audio, and piCorePlayer.

## Architecture

### Backend

The backend is built with FastAPI and provides:

- REST API for all functionality
- WebSocket connections for real-time updates
- MPD integration for audio playback
- SQLite database for local storage
- Media library scanning and indexing

### Frontend

The frontend is built with React and provides:

- Touch-friendly Material Design 3 UI
- Real-time playback controls
- Library browsing
- Playlist management
- System settings

## API Endpoints

### Music Library

- `GET /api/v1/music` - Get music tracks
- `GET /api/v1/albums` - Get albums
- `GET /api/v1/artists` - Get artists
- `GET /api/v1/music/search` - Search music
- `GET /api/v1/music/stats` - Get music library statistics

### Queue Management

- `GET /api/v1/queue` - Get current queue
- `POST /api/v1/queue/add` - Add track to queue
- `POST /api/v1/queue/remove` - Remove track from queue
- `POST /api/v1/queue/clear` - Clear queue
- `POST /api/v1/queue/move` - Move track in queue
- `POST /api/v1/queue/play/{track_id}` - Play specific track

### Playback Control

- `GET /api/v1/playback/status` - Get playback status
- `POST /api/v1/playback/play` - Start playback
- `POST /api/v1/playback/pause` - Pause/resume playback
- `POST /api/v1/playback/stop` - Stop playback
- `POST /api/v1/playback/next` - Skip to next track
- `POST /api/v1/playback/previous` - Go to previous track
- `POST /api/v1/playback/seek` - Seek to position
- `POST /api/v1/playback/volume` - Set volume
- `POST /api/v1/playback/mode/repeat` - Set repeat mode
- `POST /api/v1/playback/mode/random` - Set random mode

### Playlists

- `GET /api/v1/playlists` - Get all playlists
- `GET /api/v1/playlists/{id}` - Get playlist by ID
- `POST /api/v1/playlists` - Create playlist
- `PUT /api/v1/playlists/{id}` - Update playlist
- `DELETE /api/v1/playlists/{id}` - Delete playlist
- `POST /api/v1/playlists/{id}/play` - Play playlist

### Artwork

- `GET /api/v1/artwork/{hash}` - Get artwork by hash
- `GET /api/v1/artwork/track/{id}` - Get track artwork
- `GET /api/v1/artwork/album/{id}` - Get album artwork
- `POST /api/v1/artwork/scan` - Scan for artwork
- `POST /api/v1/artwork/clear` - Clear artwork cache

### Settings

- `GET /api/v1/settings/system` - Get system settings
- `POST /api/v1/settings/scan` - Start library scan
- `GET /api/v1/settings/scan/status` - Get scan status
- `POST /api/v1/settings/mpd/update` - Update MPD database

### Bluetooth

- `GET /api/v1/bluetooth/devices` - Get paired devices
- `POST /api/v1/bluetooth/scan` - Start device scan
- `POST /api/v1/bluetooth/connect/{address}` - Connect to device
- `POST /api/v1/bluetooth/disconnect/{address}` - Disconnect device
- `POST /api/v1/bluetooth/remove/{address}` - Remove device
- `GET /api/v1/bluetooth/status` - Get Bluetooth status

### WiFi

- `GET /api/v1/wifi/networks` - Get available networks
- `POST /api/v1/wifi/connect` - Connect to network
- `POST /api/v1/wifi/disconnect` - Disconnect from network
- `GET /api/v1/wifi/status` - Get WiFi status
- `POST /api/v1/wifi/scan` - Scan for networks

## WebSocket Events

### Player Events

```json
{
  "type": "player_event",
  "events": ["player", "playlist", "mixer", "options"],
  "status": {...},
  "song": {...}
}
```

### Queue Updates

```json
{
  "type": "queue_update",
  "queue": [...],
  "status": {...}
}
```

### Library Updates

```json
{
  "type": "library_update",
  "stats": {...}
}
```

## Database Schema

### Tables

- `tracks` - Music tracks
- `albums` - Album information
- `artists` - Artist information
- `playlists` - Playlist definitions
- `playlist_tracks` - Playlist track associations
- `queue_items` - Current queue items
- `file_hashes` - File hash tracking
- `scan_states` - Scan state tracking

## Configuration

### Environment Variables

- `TOUCHPLAYER_DB_PATH` - Database path (default: `/opt/touchplayer/data/touchplayer.db`)
- `TOUCHPLAYER_MUSIC_DIR` - MPD-relative music directory (default: `/home/pi/Music`)

### MPD Configuration

The MPD configuration is located at `/etc/mpd.conf`. Key settings:

- Audio output: PipeWire, selected through Settings > Audio Output
- Music directory: `/home/pi/Music`
- Port: 6600
- PipeWire runtime: `/run/user/1000`

## Troubleshooting

### Services not starting

```bash
# Check service status
systemctl status touchplayer-api
systemctl status touchplayer-mpd-listener
systemctl status touchplayer-indexer
systemctl status touchplayer-bluetooth
systemctl status mpd nginx bluetooth

# Check logs
journalctl -u touchplayer-api -f
journalctl -u touchplayer-mpd-listener -f
```

### MPD connection issues

```bash
# Check MPD status
systemctl status mpd

# Restart MPD
sudo systemctl restart mpd
```

### Frontend not loading

```bash
# Check nginx status
systemctl status nginx

# Check nginx logs
tail -f /var/log/nginx/error.log
```

### Permission issues

```bash
# Fix permissions
sudo chown -R pi:pi /opt/touchplayer
sudo chown -R pi:pi /home/pi/Music
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.
