"""
TouchPlayer File Utilities
"""
import os
import hashlib
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return ""


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get file metadata"""
    try:
        stat = os.stat(file_path)
        return {
            "file_size": stat.st_size,
            "file_modified": datetime.fromtimestamp(stat.st_mtime),
        }
    except Exception as e:
        print(f"Error getting file info for {file_path}: {e}")
        return {"file_size": 0, "file_modified": datetime.utcnow()}


def is_supported_file(file_path: str, supported_extensions: list = None) -> bool:
    """Check if file has supported extension"""
    if supported_extensions is None:
        supported_extensions = [
            ".mp3", ".flac", ".wav", ".aac", ".ogg", ".oga", ".wma", ".m4a", ".m4b", ".opus", ".webm",
            ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm"
        ]
    ext = Path(file_path).suffix.lower()
    return ext in supported_extensions
