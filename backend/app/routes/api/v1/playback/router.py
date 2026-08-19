"""
TouchPlayer Playback API Routes
Playback control endpoints
"""
import os
import re
import subprocess
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models import Track
from app.services.mpd_service import mpd_service
from app.services.queue.manager import queue_manager

router = APIRouter()


def _pipewire_env() -> dict:
    """Environment so wpctl can reach the user's PipeWire session"""
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    return env


def _get_output_volume() -> Optional[int]:
    """Read the active PipeWire sink volume used by external speaker controls."""
    try:
        result = subprocess.run(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
            capture_output=True,
            text=True,
            timeout=5,
            env=_pipewire_env(),
        )
        match = re.search(r"Volume:\s*([0-9.]+)", result.stdout)
        if result.returncode == 0 and match:
            return max(0, min(100, round(float(match.group(1)) * 100)))
    except Exception:
        pass
    return None


@router.get("/playback/status")
async def get_status():
    """Get playback status"""
    try:
        status = await mpd_service.status()
        current_song = await mpd_service.currentsong()
        output_volume = _get_output_volume()
        return {
            "status": status,
            "output_volume": output_volume,
            "current_song": current_song,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MPD connection failed: {e}")


@router.post("/playback/play")
async def play(song_id: Optional[int] = None):
    """Start playback"""
    try:
        result = await mpd_service.play(song_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to play: {e}")


@router.post("/playback/pause")
async def pause(pause: bool = True):
    """Pause/resume playback"""
    try:
        result = await mpd_service.pause(pause)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to pause: {e}")


@router.post("/playback/stop")
async def stop():
    """Stop playback"""
    try:
        result = await mpd_service.stop()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to stop: {e}")


@router.post("/playback/next")
async def next_track():
    """Skip to next track"""
    try:
        result = await mpd_service.next()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to skip: {e}")


@router.post("/playback/previous")
async def previous_track():
    """Go to previous track"""
    try:
        result = await mpd_service.previous()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to go to previous: {e}")


@router.post("/playback/seek")
async def seek(song_id: int, time_pos: int):
    """Seek to position"""
    try:
        result = await mpd_service.seekid(song_id, time_pos)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to seek: {e}")


@router.post("/playback/volume")
async def set_volume(volume: int):
    """Set volume (0-100)"""
    if volume < 0 or volume > 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    
    try:
        result = await mpd_service.set_volume(100)
        pipewire_result = subprocess.run(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume}%"],
            capture_output=True,
            text=True,
            timeout=10,
            env=_pipewire_env(),
        )
        if pipewire_result.returncode != 0:
            raise RuntimeError(pipewire_result.stderr.strip() or "Failed to set speaker volume")
        return {"success": True, "volume": volume}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to set volume: {e}")


@router.post("/playback/volume/up")
async def volume_up(step: int = 5):
    """Increase volume"""
    try:
        result = await mpd_service.volume_up(step)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to increase volume: {e}")


@router.post("/playback/volume/down")
async def volume_down(step: int = 5):
    """Decrease volume"""
    try:
        result = await mpd_service.volume_down(step)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to decrease volume: {e}")


@router.get("/playback/outputs")
async def get_audio_outputs():
    """List available audio output devices (PipeWire sinks)"""
    try:
        result = subprocess.run(
            ["wpctl", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            env=_pipewire_env(),
        )
        if result.returncode != 0:
            return {"outputs": []}

        outputs = []
        in_sinks = False
        for line in result.stdout.splitlines():
            if "Sinks:" in line:
                in_sinks = True
                continue
            if in_sinks and re.search(r"(Sources|Filters|Streams|Devices):", line):
                break
            if in_sinks:
                match = re.search(r"(\*)?\s*(\d+)\.\s+(.+?)\s+\[vol", line)
                if match:
                    outputs.append({
                        "id": int(match.group(2)),
                        "name": match.group(3).strip(),
                        "active": match.group(1) == "*",
                    })
        return {"outputs": outputs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list audio outputs: {e}")


@router.post("/playback/output")
async def set_audio_output(sink_id: int):
    """Route audio to the given PipeWire sink by making it the default"""
    try:
        result = subprocess.run(
            ["wpctl", "set-default", str(sink_id)],
            capture_output=True,
            text=True,
            timeout=10,
            env=_pipewire_env(),
        )
        if result.returncode == 0:
            return {"success": True, "sink_id": sink_id}
        raise HTTPException(status_code=500, detail=result.stderr.strip() or "Failed to set output")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set audio output: {e}")


@router.post("/playback/mode/repeat")
async def set_repeat(repeat: bool):
    """Enable/disable repeat mode"""
    try:
        result = await mpd_service.set_repeat(repeat)
        return {"success": True, "repeat": repeat}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to set repeat: {e}")


@router.post("/playback/mode/random")
async def set_random(random: bool):
    """Enable/disable random mode"""
    try:
        result = await mpd_service.set_random(random)
        return {"success": True, "random": random}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to set random: {e}")


@router.post("/playback/mode/single")
async def set_single(single: bool):
    """Enable/disable single mode"""
    try:
        result = await mpd_service.set_single(single)
        return {"success": True, "single": single}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to set single: {e}")


@router.post("/playback/mode/crossfade")
async def set_crossfade(crossfade: int):
    """Set crossfade duration in seconds"""
    if crossfade < 0 or crossfade > 120:
        raise HTTPException(status_code=400, detail="Crossfade must be between 0 and 120 seconds")
    
    try:
        result = await mpd_service.set_crossfade(crossfade)
        return {"success": True, "crossfade": crossfade}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to set crossfade: {e}")


@router.post("/playback/library/track/{track_id}")
async def play_track(track_id: int, db: Session = Depends(get_session)):
    """Play a specific track from library"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        # Clear queue
        await mpd_service.clear()
        
        # Add track to queue
        await mpd_service.add(track.file_path)
        
        # Play
        await mpd_service.play()
        
        return {"success": True, "track": track.title}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to play track: {e}")


@router.post("/playback/library/album/{album_id}")
async def play_album(album_id: int, db: Session = Depends(get_session)):
    """Play an album"""
    album = db.query(Track).filter(Track.album_id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    try:
        # Clear queue
        await mpd_service.clear()
        
        # Add all tracks from album
        tracks = db.query(Track).filter(Track.album_id == album_id).order_by(Track.track_number).all()
        for track in tracks:
            await mpd_service.add(track.file_path)
        
        # Play
        await mpd_service.play()
        
        return {"success": True, "album": album.album}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to play album: {e}")


@router.post("/playback/library/artist/{artist_id}")
async def play_artist(artist_id: int, db: Session = Depends(get_session)):
    """Play an artist"""
    artist = db.query(Track).filter(Track.artist_id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    try:
        # Clear queue
        await mpd_service.clear()
        
        # Add all tracks from artist
        tracks = db.query(Track).filter(Track.artist_id == artist_id).order_by(Track.album, Track.track_number).all()
        for track in tracks:
            await mpd_service.add(track.file_path)
        
        # Play
        await mpd_service.play()
        
        return {"success": True, "artist": artist.artist}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to play artist: {e}")


@router.post("/playback/library/playlist/{playlist_id}")
async def play_playlist(playlist_id: int, db: Session = Depends(get_session)):
    """Play a playlist"""
    playlist = db.query(Track).filter(Track.playlist_tracks.any(playlist_id=playlist_id)).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    try:
        # Clear queue
        await mpd_service.clear()
        
        # Add all tracks from playlist
        from app.database.models import PlaylistTrack
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        for pt in tracks:
            await mpd_service.add(pt.track.file_path)
        
        # Play
        await mpd_service.play()
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to play playlist: {e}")
