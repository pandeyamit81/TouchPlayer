"""
TouchPlayer Database Models
"""
import hashlib
import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
    event,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from .session import Base


class Track(Base):
    """Music track model"""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(1024), nullable=False, unique=True, index=True)
    file_hash = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    artist = Column(String(512), nullable=False, index=True)
    album = Column(String(512), nullable=False, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    
    # Metadata
    duration = Column(Float, nullable=False, default=0.0)
    track_number = Column(Integer, nullable=True)
    disc_number = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String(128), nullable=True)
    
    # Playback stats
    play_count = Column(Integer, nullable=False, default=0)
    skip_count = Column(Integer, nullable=False, default=0)
    favorite = Column(Boolean, nullable=False, default=False)
    rating = Column(Integer, nullable=True)  # 1-5
    last_played = Column(DateTime, nullable=True)
    
    # File info
    file_size = Column(Integer, nullable=False)
    file_modified = Column(DateTime, nullable=False)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    album_obj = relationship("Album", back_populates="tracks")
    artist_obj = relationship("Artist", back_populates="tracks")
    queue_items = relationship("QueueItem", back_populates="track", cascade="all, delete-orphan")
    playlist_tracks = relationship("PlaylistTrack", back_populates="track", cascade="all, delete-orphan")
    transcript = relationship("TrackTranscript", back_populates="track", uselist=False, cascade="all, delete-orphan")
    enrichment = relationship("TrackEnrichment", back_populates="track", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_track_artist_album", "artist", "album"),
        Index("idx_track_file_hash", "file_hash"),
    )

    @validates("rating")
    def validate_rating(self, key, value):
        if value is not None and (value < 1 or value > 5):
            raise ValueError("Rating must be between 1 and 5")
        return value


class Album(Base):
    """Album model"""
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, index=True)
    artist = Column(String(512), nullable=False, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String(128), nullable=True)
    track_count = Column(Integer, nullable=False, default=0)
    duration = Column(Float, nullable=False, default=0.0)
    has_artwork = Column(Boolean, nullable=False, default=False)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    artist_obj = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album_obj", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_album_name_artist", "name", "artist"),
    )


class Artist(Base):
    """Artist model"""
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, unique=True, index=True)
    sort_name = Column(String(512), nullable=True)
    genre = Column(String(128), nullable=True)
    bio = Column(Text, nullable=True)
    image_path = Column(String(1024), nullable=True)
    track_count = Column(Integer, nullable=False, default=0)
    album_count = Column(Integer, nullable=False, default=0)
    play_count = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    albums = relationship("Album", back_populates="artist_obj", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="artist_obj", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_artist_sort_name", "sort_name"),
    )


class Playlist(Base):
    """Playlist model"""
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)  # System playlists can't be deleted
    track_count = Column(Integer, nullable=False, default=0)
    duration = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrack(Base):
    """Playlist track association"""
    __tablename__ = "playlist_tracks"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    playlist = relationship("Playlist", back_populates="tracks")
    track = relationship("Track", back_populates="playlist_tracks")
    
    __table_args__ = (
        Index("idx_playlist_track_playlist", "playlist_id", "position", unique=True),
        Index("idx_playlist_track_track", "track_id"),
    )


class TrackTranscript(Base):
    """Cached Whisper transcription state for a track."""
    __tablename__ = "track_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="pending")
    text = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    model = Column(String(128), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    track = relationship("Track", back_populates="transcript")


class TrackEnrichment(Base):
    """Internet metadata cached for a track without overwriting source tags."""
    __tablename__ = "track_enrichments"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, unique=True)
    composer = Column(String(512), nullable=True)
    source = Column(String(128), nullable=True)
    source_id = Column(String(128), nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    track = relationship("Track", back_populates="enrichment")


class QueueItem(Base):
    """Queue item model"""
    __tablename__ = "queue_items"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    added_by = Column(String(128), nullable=True)  # User who added the track
    
    # Relationships
    track = relationship("Track", back_populates="queue_items")
    
    __table_args__ = (
        Index("idx_queue_position", "position", unique=True),
        Index("idx_queue_track", "track_id"),
    )


class FileHash(Base):
    """File hash tracking for incremental scans"""
    __tablename__ = "file_hashes"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(1024), nullable=False, unique=True, index=True)
    file_hash = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_modified = Column(DateTime, nullable=False)
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_hash_file_path", "file_path"),
        Index("idx_hash_file_hash", "file_hash"),
    )


class ScanState(Base):
    """Scan state tracking"""
    __tablename__ = "scan_states"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(64), nullable=False, unique=True, index=True)  # full, incremental
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, running, completed, failed
    total_files = Column(Integer, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    new_files = Column(Integer, nullable=False, default=0)
    modified_files = Column(Integer, nullable=False, default=0)
    deleted_files = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    
    def start(self):
        """Mark scan as started"""
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.status = "running"
        self.error = None
        self.processed_files = 0
    
    def complete(self, total_files: int = 0, new_files: int = 0, modified_files: int = 0, deleted_files: int = 0):
        """Mark scan as completed"""
        self.completed_at = datetime.utcnow()
        self.status = "completed"
        self.total_files = total_files
        self.new_files = new_files
        self.modified_files = modified_files
        self.deleted_files = deleted_files
    
    def fail(self, error: str):
        """Mark scan as failed"""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
        self.error = error


# Event listeners for updating timestamps
@event.listens_for(Track, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(Album, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(Artist, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(Playlist, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
