"""
TouchPlayer Pydantic Models
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class Track(BaseModel):
    """Track model"""
    id: int
    file_path: str
    title: str
    artist: str
    album: str
    duration: float
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    play_count: int = 0
    skip_count: int = 0
    favorite: bool = False
    rating: Optional[int] = None
    last_played: Optional[datetime] = None
    file_size: int = 0
    file_modified: datetime
    added_at: datetime
    updated_at: datetime


class Album(BaseModel):
    """Album model"""
    id: int
    name: str
    artist: str
    artist_id: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    track_count: int = 0
    duration: float = 0.0
    has_artwork: bool = False
    added_at: datetime
    updated_at: datetime


class Artist(BaseModel):
    """Artist model"""
    id: int
    name: str
    sort_name: Optional[str] = None
    genre: Optional[str] = None
    bio: Optional[str] = None
    image_path: Optional[str] = None
    track_count: int = 0
    album_count: int = 0
    play_count: int = 0
    added_at: datetime
    updated_at: datetime


class Playlist(BaseModel):
    """Playlist model"""
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool = False
    track_count: int = 0
    duration: float = 0.0
    created_at: datetime
    updated_at: datetime


class PlaylistTrack(BaseModel):
    """Playlist track association"""
    id: int
    playlist_id: int
    track_id: int
    position: int
    added_at: datetime


class QueueItem(BaseModel):
    """Queue item model"""
    id: int
    track_id: int
    position: int
    added_at: datetime
    added_by: Optional[str] = None


class PlayerState(BaseModel):
    """Player state model"""
    is_playing: bool = False
    is_paused: bool = False
    is_stopped: bool = True
    current_track: Optional[Track] = None
    queue: List[Track] = []
    volume: int = 50
    repeat: bool = False
    random: bool = False
    single: bool = False
    crossfade: int = 0


class ScanStats(BaseModel):
    """Scan statistics model"""
    total_files: int = 0
    processed_files: int = 0
    new_files: int = 0
    modified_files: int = 0
    deleted_files: int = 0
