"""
TouchPlayer Playlist Manager
Manages playlists
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_session
from app.database.models import Track, Playlist, PlaylistTrack, QueueItem
from app.services.mpd_service import mpd_service


class PlaylistManager:
    """Playlist manager service"""
    
    def get_system_playlists(self) -> List[Dict[str, Any]]:
        """Get system playlists"""
        return [
            {"id": "all", "name": "All Tracks", "description": "All tracks in library", "is_system": True},
            {"id": "favorites", "name": "Favorites", "description": "Favorite tracks", "is_system": True},
            {"id": "recent", "name": "Recently Played", "description": "Recently played tracks", "is_system": True},
            {"id": "random", "name": "Random", "description": "Random tracks", "is_system": True},
        ]
    
    async def get_playlists(self, db: Session) -> List[Dict[str, Any]]:
        """Get all playlists"""
        playlists = db.query(Playlist).filter(Playlist.is_system == False).all()
        result = []
        for playlist in playlists:
            track_count = db.query(func.count(PlaylistTrack.id)).filter(PlaylistTrack.playlist_id == playlist.id).scalar()
            result.append({
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
                "track_count": track_count or 0,
                "duration": playlist.duration,
                "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
                "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
            })
        return result
    
    async def get_playlist(self, db: Session, playlist_id: int) -> Optional[Dict[str, Any]]:
        """Get playlist by ID"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return None
        
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        track_list = []
        for pt in tracks:
            track = pt.track
            track_list.append({
                "id": track.id,
                "file_path": track.file_path,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "duration": track.duration,
                "track_number": track.track_number,
                "play_count": track.play_count,
                "favorite": track.favorite,
            })
        
        return {
            "id": playlist.id,
            "name": playlist.name,
            "description": playlist.description,
            "track_count": len(track_list),
            "duration": playlist.duration,
            "tracks": track_list,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
        }
    
    async def create_playlist(self, db: Session, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new playlist"""
        playlist = Playlist(
            name=name,
            description=description,
            is_system=False,
        )
        db.add(playlist)
        db.commit()
        
        return {
            "success": True,
            "playlist_id": playlist.id,
        }
    
    async def update_playlist(self, db: Session, playlist_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Update playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        if name:
            playlist.name = name
        if description:
            playlist.description = description
        
        db.commit()
        
        return {"success": True}
    
    def _to_mpd_uri(self, file_path: str) -> str:
        music_dir = os.environ.get("TOUCHPLAYER_MUSIC_DIR", "/home/pi/Music")
        if os.path.isabs(file_path):
            relative_path = os.path.relpath(file_path, music_dir)
            if not relative_path.startswith(".."):
                return relative_path
        return file_path
    async def delete_playlist(self, db: Session, playlist_id: int) -> Dict[str, Any]:
        """Delete playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        if playlist.is_system:
            return {"error": "Cannot delete system playlist"}
        
        # Delete playlist tracks
        db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
        
        # Delete playlist
        db.delete(playlist)
        db.commit()
        
        return {"success": True}
    
    async def add_to_playlist(self, db: Session, playlist_id: int, track_id: int) -> Dict[str, Any]:
        """Add track to playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return {"error": "Track not found"}
        
        # Check if track already in playlist
        existing = db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        ).first()
        if existing:
            return {"error": "Track already in playlist"}
        
        # Get position
        max_position = db.query(func.max(PlaylistTrack.position)).filter(PlaylistTrack.playlist_id == playlist_id).scalar()
        position = (max_position or -1) + 1
        
        # Add track to playlist
        playlist_track = PlaylistTrack(
            playlist_id=playlist_id,
            track_id=track_id,
            position=position,
        )
        db.add(playlist_track)
        
        # Update playlist stats
        playlist.track_count += 1
        playlist.duration += track.duration
        
        db.commit()
        
        return {"success": True}
    
    async def remove_from_playlist(self, db: Session, playlist_id: int, track_id: int) -> Dict[str, Any]:
        """Remove track from playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        playlist_track = db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        ).first()
        if not playlist_track:
            return {"error": "Track not in playlist"}
        
        # Get track duration
        track = playlist_track.track
        if track:
            playlist.duration = max(0, playlist.duration - track.duration)
        
        db.delete(playlist_track)
        
        # Update track count
        playlist.track_count = db.query(func.count(PlaylistTrack.id)).filter(PlaylistTrack.playlist_id == playlist_id).scalar()
        
        # Reorder remaining tracks
        self._reorder_playlist(db, playlist_id)
        
        db.commit()
        
        return {"success": True}
    
    async def move_in_playlist(self, db: Session, playlist_id: int, from_position: int, to_position: int) -> Dict[str, Any]:
        """Move track in playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        from_item = db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.position == from_position,
        ).first()
        to_item = db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.position == to_position,
        ).first()
        
        if from_item:
            from_item.position = to_position
        if to_item:
            to_item.position = from_position
        
        db.commit()
        
        return {"success": True}
    
    async def play_playlist(self, db: Session, playlist_id: int) -> Dict[str, Any]:
        """Play playlist"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        # Clear queue
        await mpd_service.clear()
        
        # Add tracks to queue
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        for pt in tracks:
            try:
                await mpd_service.add(self._to_mpd_uri(pt.track.file_path))
            except Exception as e:
                logger.error(f"Failed to add track to queue: {e}")
        
        # Play first track
        try:
            await mpd_service.play()
        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return {"error": str(e)}
        
        return {"success": True}
    
    async def load_playlist_into_queue(self, db: Session, playlist_id: int) -> Dict[str, Any]:
        """Load playlist into queue (without playing)"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Playlist not found"}
        
        # Clear queue
        await mpd_service.clear()
        
        # Add tracks to queue
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        for pt in tracks:
            try:
                await mpd_service.add(self._to_mpd_uri(pt.track.file_path))
            except Exception as e:
                logger.error(f"Failed to add track to queue: {e}")
        
        return {"success": True}
    
    async def get_playlist_tracks(self, db: Session, playlist_id: int) -> List[Dict[str, Any]]:
        """Get playlist tracks"""
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return []
        
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        result = []
        for pt in tracks:
            track = pt.track
            result.append({
                "id": track.id,
                "file_path": track.file_path,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "duration": track.duration,
                "track_number": track.track_number,
                "play_count": track.play_count,
                "favorite": track.favorite,
            })
        return result
    
    def _reorder_playlist(self, db: Session, playlist_id: int):
        """Reorder playlist positions after removal"""
        tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()
        for i, track in enumerate(tracks):
            track.position = i
        db.commit()
    
    async def get_system_playlist_tracks(self, db: Session, playlist_type: str) -> List[Dict[str, Any]]:
        """Get tracks for system playlist"""
        if playlist_type == "all":
            tracks = db.query(Track).order_by(Track.added_at.desc()).all()
        elif playlist_type == "favorites":
            tracks = db.query(Track).filter(Track.favorite == True).order_by(Track.last_played.desc()).all()
        elif playlist_type == "recent":
            tracks = db.query(Track).filter(Track.last_played.isnot(None)).order_by(Track.last_played.desc()).all()
        elif playlist_type == "random":
            tracks = db.query(Track).order_by(func.random()).limit(100).all()
        else:
            return []
        
        result = []
        for track in tracks:
            result.append({
                "id": track.id,
                "file_path": track.file_path,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "duration": track.duration,
                "track_number": track.track_number,
                "play_count": track.play_count,
                "favorite": track.favorite,
            })
        return result


# Global instance
playlist_manager = PlaylistManager()
