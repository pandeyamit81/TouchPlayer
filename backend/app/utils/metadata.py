"""
TouchPlayer Metadata Utilities
"""
import subprocess
from pathlib import Path
from typing import Dict, Any


def extract_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from file using FFmpeg"""
    try:
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
        print(f"Error extracting metadata from {file_path}: {e}")
    
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
