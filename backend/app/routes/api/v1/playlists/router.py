"""
TouchPlayer Playlists API Routes
Playlist management endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models import Playlist, PlaylistTrack, Track
from app.services.playlists.manager import playlist_manager

router = APIRouter()


@router.get("/playlists")
async def get_playlists(db: Session = Depends(get_session)):
    """Get all playlists"""
    return await playlist_manager.get_playlists(db)


@router.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: int, db: Session = Depends(get_session)):
    """Get playlist by ID"""
    playlist = await playlist_manager.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.post("/playlists")
async def create_playlist(
    name: str,
    description: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """Create a new playlist"""
    return await playlist_manager.create_playlist(db, name, description)


@router.put("/playlists/{playlist_id}")
async def update_playlist(
    playlist_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """Update playlist"""
    result = await playlist_manager.update_playlist(db, playlist_id, name, description)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: int, db: Session = Depends(get_session)):
    """Delete playlist"""
    result = await playlist_manager.delete_playlist(db, playlist_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/playlists/{playlist_id}/tracks")
async def add_to_playlist(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_session),
):
    """Add track to playlist"""
    result = await playlist_manager.add_to_playlist(db, playlist_id, track_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/playlists/{playlist_id}/tracks/{track_id}")
async def remove_from_playlist(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_session),
):
    """Remove track from playlist"""
    result = await playlist_manager.remove_from_playlist(db, playlist_id, track_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/playlists/{playlist_id}/play")
async def play_playlist(playlist_id: int, db: Session = Depends(get_session)):
    """Play playlist"""
    result = await playlist_manager.play_playlist(db, playlist_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/playlists/{playlist_id}/tracks")
async def get_playlist_tracks(playlist_id: int, db: Session = Depends(get_session)):
    """Get playlist tracks"""
    return await playlist_manager.get_playlist_tracks(db, playlist_id)
