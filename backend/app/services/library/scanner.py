"""
TouchPlayer Media Library Scanner
Scans media files and updates the database
"""
import os
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database.session import get_session, engine
from app.database.models import Track, Album, Artist, FileHash, ScanState, Playlist
from app.services.mpd_service import mpd_service

DEFAULT_MEDIA_DIRS = ["/media", "/mnt/usb", "/home/pi/Music"]


def get_scan_dirs() -> List[str]:
    """Return default media roots plus the active Samba share, if configured."""
    media_dirs = DEFAULT_MEDIA_DIRS.copy()
    try:
        from app.services.samba.manager import samba_manager

        share = samba_manager.get_share()
        if share and share.get("path"):
            media_dirs.append(os.path.abspath(share["path"]))
    except Exception as e:
        logger.warning(f"Failed to load Samba share for scanning: {e}")
    return list(dict.fromkeys(media_dirs))


class MediaScanner:
    """Media library scanner"""
    
    def __init__(
        self,
        media_dirs: Optional[List[str]] = None,
        supported_extensions: Optional[List[str]] = None,
    ):
        self.media_dirs = get_scan_dirs() if media_dirs is None else media_dirs
        self.supported_extensions = supported_extensions or [
            ".mp3", ".flac", ".wav", ".aac", ".ogg", ".oga", ".wma", ".m4a", ".m4b", ".opus", ".webm",
            ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm"
        ]
        self._scan_cancelled = False
        self._scan_progress = {"total": 0, "processed": 0, "new": 0, "modified": 0, "deleted": 0}
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            stat = os.stat(file_path)
            return {
                "file_size": stat.st_size,
                "file_modified": datetime.fromtimestamp(stat.st_mtime),
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {"file_size": 0, "file_modified": datetime.utcnow()}
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file has supported extension"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    @staticmethod
    def _file_changed(stored: FileHash, file_info: Dict[str, Any]) -> bool:
        """Compare file metadata with tolerance for filesystem timestamp precision."""
        modified_delta = abs((stored.file_modified - file_info["file_modified"]).total_seconds())
        return stored.file_size != file_info["file_size"] or modified_delta > 1
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file using FFmpeg"""
        # Try to use FFmpeg to extract metadata
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                import json
                metadata = json.loads(result.stdout)
                info = {
                    "title": "",
                    "artist": "",
                    "album": "",
                    "duration": 0.0,
                    "track_number": None,
                    "disc_number": None,
                    "year": None,
                    "genre": "",
                }
                
                # Extract from format
                if "format" in metadata and "tags" in metadata["format"]:
                    tags = metadata["format"]["tags"]
                    info["title"] = tags.get("title", "") or Path(file_path).stem
                    info["artist"] = tags.get("artist", "")
                    info["album"] = tags.get("album", "")
                    info["duration"] = float(metadata["format"].get("duration", 0))
                    info["year"] = tags.get("date", "")[:4] if tags.get("date") else None
                    info["genre"] = tags.get("genre", "")
                
                # Extract from streams (for video files)
                if "streams" in metadata:
                    for stream in metadata["streams"]:
                        if stream.get("codec_type") == "video":
                            info["duration"] = float(metadata["format"].get("duration", 0))
                            break
                
                # Fallback to filename if no metadata
                if not info["title"]:
                    info["title"] = Path(file_path).stem
                
                return info
        except Exception as e:
            logger.warning(f"Error extracting metadata from {file_path}: {e}")
        
        # Fallback to filename-based metadata
        filename = Path(file_path).stem
        parts = filename.split(" - ")
        return {
            "title": parts[-1] if parts else filename,
            "artist": parts[0] if len(parts) > 1 else "Unknown Artist",
            "album": parts[1] if len(parts) > 2 else "Unknown Album",
            "duration": 0.0,
            "track_number": None,
            "disc_number": None,
            "year": None,
            "genre": "",
        }
    
    def get_all_files(self) -> List[str]:
        """Get all supported files in media directories"""
        files = []
        for media_dir in self.media_dirs:
            if os.path.exists(media_dir):
                for root, dirs, filenames in os.walk(media_dir):
                    for filename in filenames:
                        if self.is_supported_file(filename):
                            files.append(os.path.join(root, filename))
        return files
    
    async def scan(self, db: Session, full_scan: bool = False) -> Dict[str, Any]:
        """Scan media library"""
        self._scan_cancelled = False
        self._scan_progress = {"total": 0, "processed": 0, "new": 0, "modified": 0, "deleted": 0}
        
        # Create scan state
        scan_state = db.query(ScanState).filter_by(scan_type="full" if full_scan else "incremental").first()
        if not scan_state:
            scan_state = ScanState(scan_type="full" if full_scan else "incremental")
            db.add(scan_state)
            db.commit()
        
        scan_state.start()
        db.commit()
        
        try:
            # Get current files
            current_files = set(self.get_all_files())
            self._scan_progress["total"] = len(current_files)
            
            # Get stored file hashes
            stored_hashes = {fh.file_path: fh for fh in db.query(FileHash).all()}
            stored_paths = set(stored_hashes.keys())
            
            # Find new and modified files
            new_files = current_files - stored_paths
            modified_files = set()
            
            if not full_scan:
                # Check for modified files
                for path in stored_paths & current_files:
                    file_info = self.get_file_info(path)
                    stored = stored_hashes[path]
                    if self._file_changed(stored, file_info):
                        modified_files.add(path)
            
            # Find deleted files
            deleted_files = stored_paths - current_files
            
            # Process new files
            for file_path in new_files:
                if self._scan_cancelled:
                    break
                await self._process_new_file(db, file_path)
                self._scan_progress["new"] += 1
                self._scan_progress["processed"] += 1
            
            # Process modified files
            for file_path in modified_files:
                if self._scan_cancelled:
                    break
                await self._process_modified_file(db, file_path, stored_hashes[file_path])
                self._scan_progress["modified"] += 1
                self._scan_progress["processed"] += 1
            
            # Process deleted files
            for file_path in deleted_files:
                if self._scan_cancelled:
                    break
                await self._process_deleted_file(db, file_path)
                self._scan_progress["deleted"] += 1
                self._scan_progress["processed"] += 1
            
            # Update file hashes
            for file_path in current_files:
                file_info = self.get_file_info(file_path)
                
                stored = stored_hashes.get(file_path)
                if stored:
                    if self._file_changed(stored, file_info) or full_scan:
                        stored.file_hash = self.calculate_file_hash(file_path)
                    stored.file_size = file_info["file_size"]
                    stored.file_modified = file_info["file_modified"]
                    stored.scanned_at = datetime.utcnow()
                else:
                    db.add(FileHash(
                        file_path=file_path,
                        file_hash=self.calculate_file_hash(file_path),
                        file_size=file_info["file_size"],
                        file_modified=file_info["file_modified"],
                    ))
            
            db.commit()
            
            # Update scan state
            scan_state.complete(
                total_files=len(current_files),
                new_files=self._scan_progress["new"],
                modified_files=self._scan_progress["modified"],
                deleted_files=self._scan_progress["deleted"],
            )
            db.commit()
            
            # Update MPD database
            try:
                await mpd_service.update()
            except Exception as e:
                logger.warning(f"Failed to update MPD database: {e}")
            
            return self._scan_progress
            
        except Exception as e:
            scan_state.fail(str(e))
            db.commit()
            logger.error(f"Scan failed: {e}")
            raise
    
    async def _process_new_file(self, db: Session, file_path: str):
        """Process a new file"""
        file_info = self.get_file_info(file_path)
        metadata = self.extract_metadata(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        # Get or create artist
        artist_name = metadata["artist"] or "Unknown Artist"
        artist = db.query(Artist).filter(func.lower(Artist.name) == func.lower(artist_name)).first()
        if not artist:
            artist = Artist(name=artist_name, sort_name=artist_name)
            db.add(artist)
            db.flush()
        
        # Get or create album
        album_name = metadata["album"] or "Unknown Album"
        album = db.query(Album).filter(
            func.lower(Album.name) == func.lower(album_name),
            func.lower(Album.artist) == func.lower(artist_name),
        ).first()
        if not album:
            album = Album(
                name=album_name,
                artist=artist_name,
                artist_id=artist.id,
                year=metadata["year"],
                genre=metadata["genre"],
            )
            db.add(album)
            db.flush()
        
        # Create track
        track = Track(
            file_path=file_path,
            file_hash=file_hash,
            title=metadata["title"],
            artist=artist_name,
            album=album_name,
            album_id=album.id,
            artist_id=artist.id,
            duration=metadata["duration"],
            track_number=metadata["track_number"],
            disc_number=metadata["disc_number"],
            year=metadata["year"],
            genre=metadata["genre"],
            file_size=file_info["file_size"],
            file_modified=file_info["file_modified"],
        )
        db.add(track)
        
        # Update artist/album stats
        artist.track_count += 1
        album.track_count += 1
        album.duration += metadata["duration"]
        
        db.flush()
    
    async def _process_modified_file(self, db: Session, file_path: str, stored_hash: FileHash):
        """Process a modified file"""
        # Delete old track
        track = db.query(Track).filter(Track.file_path == file_path).first()
        if track:
            db.delete(track)
        
        # Re-process as new file
        await self._process_new_file(db, file_path)
    
    async def _process_deleted_file(self, db: Session, file_path: str):
        """Process a deleted file"""
        track = db.query(Track).filter(Track.file_path == file_path).first()
        if track:
            # Update artist/album stats
            if track.artist_obj:
                track.artist_obj.track_count = max(0, track.artist_obj.track_count - 1)
            if track.album_obj:
                track.album_obj.track_count = max(0, track.album_obj.track_count - 1)
                track.album_obj.duration = max(0, track.album_obj.duration - track.duration)
            
            db.delete(track)

        file_hash = db.query(FileHash).filter(FileHash.file_path == file_path).first()
        if file_hash:
            db.delete(file_hash)
    
    def cancel_scan(self):
        """Cancel ongoing scan"""
        self._scan_cancelled = True
    
    def get_progress(self) -> Dict[str, Any]:
        """Get scan progress"""
        return self._scan_progress.copy()


async def run_scan(
    full_scan: bool = False,
    media_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run media library scan"""
    scanner = MediaScanner(media_dirs=media_dirs)
    
    with next(get_session()) as db:
        return await scanner.scan(db, full_scan=full_scan)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await run_scan(full_scan=True)
        print(f"Scan complete: {result}")
    
    asyncio.run(main())
