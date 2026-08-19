"""
TouchPlayer Queue Manager
Manages the playback queue
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_session
from app.database.models import Track, QueueItem, Playlist, PlaylistTrack
from app.services.mpd_service import mpd_service

# Must match music_directory in mpd.conf; MPD only plays files under this path.
MPD_MUSIC_DIR = os.environ.get("TOUCHPLAYER_MUSIC_DIR", "/home/pi")


class QueueManager:
    """Queue manager service"""
    
    def __init__(self):
        self._current_version = 0
    
    def _to_mpd_uri(self, file_path: str) -> str:
        """Convert an absolute track path to a URI relative to MPD's music dir"""
        if os.path.isabs(file_path):
            rel = os.path.relpath(file_path, MPD_MUSIC_DIR)
            if not rel.startswith(".."):
                return rel
        return file_path
    
    async def get_queue(self, db: Session) -> List[Dict[str, Any]]:
        """Get current queue"""
        # Get queue from MPD
        try:
            queue_info = await mpd_service.playlistinfo()
            return queue_info
        except Exception as e:
            logger.error(f"Failed to get queue: {e}")
            return []
    
    async def get_queue_from_db(self, db: Session) -> List[Dict[str, Any]]:
        """Get queue from database"""
        queue_items = db.query(QueueItem).order_by(QueueItem.position).all()
        result = []
        for item in queue_items:
            track = item.track
            result.append({
                "id": track.id,
                "file_path": track.file_path,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "duration": track.duration,
                "track_number": track.track_number,
                "disc_number": track.disc_number,
                "play_count": track.play_count,
                "favorite": track.favorite,
            })
        return result
    
    async def add_to_queue(self, db: Session, track_id: int, position: Optional[int] = None, added_by: str = "system") -> Dict[str, Any]:
        """Add track to queue"""
        # Get track
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return {"error": "Track not found"}
        
        # Get current queue length and reserve the requested insertion position.
        max_position = db.query(func.max(QueueItem.position)).scalar()
        queue_length = (max_position if max_position is not None else -1) + 1
        new_position = queue_length if position is None else max(0, min(position, queue_length))
        
        # Add to MPD
        try:
            result = await mpd_service.addid(self._to_mpd_uri(track.file_path))
            if isinstance(result, dict) and "id" in result:
                mpd_song_id = int(result["id"])
            else:
                mpd_song_id = None
        except Exception as e:
            logger.error(f"Failed to add to MPD queue: {e}")
            mpd_song_id = None

        if position is not None and mpd_song_id is not None:
            try:
                await mpd_service.moveid(mpd_song_id, new_position)
            except Exception as e:
                logger.error(f"Failed to move track to queue position {new_position}: {e}")
        
        # Add to database
        queue_item = QueueItem(
            track_id=track_id,
            position=queue_length,
            added_by=added_by,
        )
        db.add(queue_item)
        db.commit()

        if new_position < queue_length:
            items = db.query(QueueItem).order_by(QueueItem.position).all()
            original_positions = {item.id: item.position for item in items}
            for item in items:
                item.position = -(item.position + 1)
            db.commit()
            for item in items:
                old_position = original_positions[item.id]
                item.position = new_position if item.id == queue_item.id else (
                    old_position + 1 if old_position >= new_position else old_position
                )
            db.commit()
        
        return {
            "success": True,
            "queue_item_id": queue_item.id,
            "position": new_position,
            "mpd_song_id": mpd_song_id,
        }
    
    async def add_uri_to_queue(self, db: Session, uri: str, added_by: str = "system") -> Dict[str, Any]:
        """Add URI to queue"""
        # Add to MPD
        try:
            result = await mpd_service.addid(uri)
            if isinstance(result, dict) and "id" in result:
                mpd_song_id = int(result["id"])
            else:
                mpd_song_id = None
        except Exception as e:
            logger.error(f"Failed to add URI to MPD queue: {e}")
            return {"error": str(e)}
        
        return {
            "success": True,
            "mpd_song_id": mpd_song_id,
        }
    
    async def remove_from_queue(self, db: Session, position: Optional[int] = None, track_id: Optional[int] = None) -> Dict[str, Any]:
        """Remove track from queue"""
        if position is not None:
            # Remove by position
            queue_item = db.query(QueueItem).filter(QueueItem.position == position).first()
            if not queue_item:
                return {"error": "Track not found at position"}
            
            # Remove from MPD
            try:
                await mpd_service.delete(position)
            except Exception as e:
                logger.error(f"Failed to remove from MPD queue: {e}")
            
            db.delete(queue_item)
            db.commit()
            
            # Reorder remaining items
            self._reorder_queue(db)
            
            return {"success": True}
        
        elif track_id is not None:
            # Remove by track ID
            queue_item = db.query(QueueItem).filter(QueueItem.track_id == track_id).first()
            if not queue_item:
                return {"error": "Track not in queue"}
            
            position = queue_item.position
            
            # Remove from MPD
            try:
                await mpd_service.delete(position)
            except Exception as e:
                logger.error(f"Failed to remove from MPD queue: {e}")
            
            db.delete(queue_item)
            db.commit()
            
            # Reorder remaining items
            self._reorder_queue(db)
            
            return {"success": True}
        
        return {"error": "Position or track_id required"}
    
    async def clear_queue(self, db: Session) -> Dict[str, Any]:
        """Clear queue"""
        # Clear MPD queue
        try:
            await mpd_service.clear()
        except Exception as e:
            logger.error(f"Failed to clear MPD queue: {e}")
        
        # Clear database
        db.query(QueueItem).delete()
        db.commit()
        
        return {"success": True}
    
    async def move_in_queue(self, db: Session, from_position: int, to_position: int) -> Dict[str, Any]:
        """Move track in queue"""
        # Move in MPD
        try:
            await mpd_service.move(from_position, to_position)
        except Exception as e:
            logger.error(f"Failed to move in MPD queue: {e}")
        
        # Move in database
        from_item = db.query(QueueItem).filter(QueueItem.position == from_position).first()
        to_item = db.query(QueueItem).filter(QueueItem.position == to_position).first()
        
        if from_item:
            from_item.position = to_position
        if to_item:
            to_item.position = from_position
        
        db.commit()
        
        return {"success": True}
    
    async def moveid_in_queue(self, db: Session, from_id: int, to_position: int) -> Dict[str, Any]:
        """Move track in queue by ID"""
        # Move in MPD
        try:
            await mpd_service.moveid(from_id, to_position)
        except Exception as e:
            logger.error(f"Failed to move in MPD queue: {e}")
        
        # Move in database
        from_item = db.query(QueueItem).filter(QueueItem.id == from_id).first()
        if from_item:
            from_item.position = to_position
        
        db.commit()
        
        return {"success": True}
    
    async def swap_in_queue(self, db: Session, pos1: int, pos2: int) -> Dict[str, Any]:
        """Swap two tracks in queue"""
        # Swap in MPD
        try:
            await mpd_service.swap(pos1, pos2)
        except Exception as e:
            logger.error(f"Failed to swap in MPD queue: {e}")
        
        # Swap in database
        item1 = db.query(QueueItem).filter(QueueItem.position == pos1).first()
        item2 = db.query(QueueItem).filter(QueueItem.position == pos2).first()
        
        if item1 and item2:
            item1.position, item2.position = item2.position, item1.position
        
        db.commit()
        
        return {"success": True}
    
    async def play_track(self, db: Session, track_id: int) -> Dict[str, Any]:
        """Play a specific track"""
        # Clear queue
        await self.clear_queue(db)
        
        # Add track to queue
        result = await self.add_to_queue(db, track_id)
        if not result.get("success"):
            return result
        
        # Play
        try:
            await mpd_service.play()
        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return {"error": str(e)}
        
        return {"success": True}
    
    async def play_queue_position(self, db: Session, position: int) -> Dict[str, Any]:
        """Play track at specific position"""
        try:
            await mpd_service.play(position)
        except Exception as e:
            logger.error(f"Failed to play position {position}: {e}")
            return {"error": str(e)}
        
        return {"success": True}
    
    def _reorder_queue(self, db: Session):
        """Reorder queue positions after removal"""
        queue_items = db.query(QueueItem).order_by(QueueItem.position).all()
        for i, item in enumerate(queue_items):
            item.position = i
        db.commit()
    
    async def get_queue_version(self, db: Session) -> int:
        """Get current queue version for change detection"""
        count = db.query(func.count(QueueItem.id)).scalar()
        return count
    
    async def get_queue_with_status(self, db: Session) -> Dict[str, Any]:
        """Get queue with current playback status"""
        queue = await self.get_queue_from_db(db)
        status = await mpd_service.status()
        current_song = await mpd_service.currentsong()
        
        return {
            "queue": queue,
            "status": status,
            "current_song": current_song,
        }


# Global instance
queue_manager = QueueManager()
