"""
TouchPlayer Playlist Models
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


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
