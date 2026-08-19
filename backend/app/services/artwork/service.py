"""
TouchPlayer Artwork Service
Generates and serves album artwork
"""
import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models import Track, Album, Artist


from pathlib import Path

class ArtworkService:
    """Artwork service for generating and serving album artwork"""
    
    def __init__(self, cache_dir: str = "/home/pi/Development/TouchPlayer/cache/artwork"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache sizes
        self.sizes = [128, 256, 512]
    
    def get_artwork_cache_path(self, hash_str: str, size: int) -> Path:
        """Get cache path for artwork"""
        return self.cache_dir / f"{hash_str}_{size}.jpg"
    
    def generate_artwork_hash(self, album_name: str, artist_name: str) -> str:
        """Generate hash for artwork"""
        hash_input = f"{album_name.lower().strip()}_{artist_name.lower().strip()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def extract_artwork_from_file(self, file_path: str) -> Optional[bytes]:
        """Extract artwork from audio file using FFmpeg"""
        try:
            import subprocess
            import tempfile
            
            # Use FFmpeg to extract artwork
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            
            result = subprocess.run(
                [
                    "ffmpeg", "-i", file_path,
                    "-an", "-vcodec", "copy",
                    "-map", "0:v:0",
                    tmp_path
                ],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    artwork = f.read()
                os.unlink(tmp_path)
                return artwork
            
            os.unlink(tmp_path)
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting artwork from {file_path}: {e}")
            return None
    
    def resize_image(self, image_data: bytes, size: int) -> bytes:
        """Resize image to specified size"""
        try:
            from PIL import Image
            import io
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Resize with high quality
            image = image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Error resizing image: {e}")
            return image_data
    
    def generate_artwork_variants(self, image_data: bytes, hash_str: str) -> Dict[str, Path]:
        """Generate artwork variants in different sizes"""
        variants = {}
        
        for size in self.sizes:
            cache_path = self.get_artwork_cache_path(hash_str, size)
            
            # Resize and save
            resized = self.resize_image(image_data, size)
            with open(cache_path, "wb") as f:
                f.write(resized)
            
            variants[str(size)] = cache_path
        
        return variants
    
    def get_artwork_for_track(self, db: Session, track_id: int, size: int = 256) -> Optional[bytes]:
        """Get artwork for a track"""
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return None
        
        return self.get_artwork_for_album(db, track.album_id, size)
    
    def get_artwork_for_album(self, db: Session, album_id: int, size: int = 256) -> Optional[bytes]:
        """Get artwork for an album"""
        album = db.query(Album).filter(Album.id == album_id).first()
        if not album:
            return None
        
        # Generate hash
        hash_str = self.generate_artwork_hash(album.name, album.artist)
        cache_path = self.get_artwork_cache_path(hash_str, size)
        
        # Check if cached
        if cache_path.exists():
            with open(cache_path, "rb") as f:
                return f.read()
        
        # Try to extract from first track
        track = db.query(Track).filter(Track.album_id == album_id).first()
        if track:
            artwork = self.extract_artwork_from_file(track.file_path)
            if artwork:
                # Generate variants
                self.generate_artwork_variants(artwork, hash_str)
                return self.resize_image(artwork, size)
        
        return None
    
    def get_artwork_for_artist(self, db: Session, artist_id: int, size: int = 256) -> Optional[bytes]:
        """Get artwork for an artist"""
        artist = db.query(Artist).filter(Artist.id == artist_id).first()
        if not artist:
            return None
        
        # Check if artist has image path
        if artist.image_path and os.path.exists(artist.image_path):
            with open(artist.image_path, "rb") as f:
                image_data = f.read()
            return self.resize_image(image_data, size)
        
        # Try to extract from first album track
        track = db.query(Track).filter(Track.artist_id == artist_id).first()
        if track:
            artwork = self.extract_artwork_from_file(track.file_path)
            if artwork:
                return self.resize_image(artwork, size)
        
        return None
    
    def get_artwork_url(self, db: Session, track_id: int, size: int = 256) -> Optional[str]:
        """Get artwork URL for a track"""
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return None
        
        hash_str = self.generate_artwork_hash(track.album, track.artist)
        return f"/api/v1/artwork/{hash_str}?size={size}"
    
    def scan_library_for_artwork(self, db: Session) -> Dict[str, int]:
        """Scan library for artwork"""
        stats = {"total": 0, "processed": 0, "found": 0}
        
        # Get all albums without artwork
        albums = db.query(Album).filter(Album.has_artwork == False).all()
        stats["total"] = len(albums)
        
        for album in albums:
            stats["processed"] += 1
            
            # Try to extract from first track
            track = db.query(Track).filter(Track.album_id == album.id).first()
            if track:
                artwork = self.extract_artwork_from_file(track.file_path)
                if artwork:
                    hash_str = self.generate_artwork_hash(album.name, album.artist)
                    self.generate_artwork_variants(artwork, hash_str)
                    album.has_artwork = True
                    stats["found"] += 1
        
        db.commit()
        return stats
    
    def clear_cache(self):
        """Clear artwork cache"""
        import shutil
        
        for size in self.sizes:
            for file_path in self.cache_dir.glob(f"*_{size}.jpg"):
                file_path.unlink()
        
        logger.info("Artwork cache cleared")


# Global instance
artwork_service = ArtworkService()
