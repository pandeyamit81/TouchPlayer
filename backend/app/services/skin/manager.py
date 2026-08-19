"""
TouchPlayer Skin Manager
Stores a user-supplied background image and its display adjustments,
used to visually skin the touchscreen UI.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

DEFAULT_SETTINGS: Dict[str, Any] = {
    "fit": "cover",  # cover, contain, repeat
    "opacity": 1.0,  # image opacity, 0-1
    "blur": 0,  # px, 0-20
    "brightness": 1.0,  # 0.2-1.5
    "overlay_color": "#000000",
    "overlay_opacity": 0.0,  # 0-1, darkens/tints the image for readability
}

MAX_DIMENSION = 2560
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class SkinManager:
    """Manages the custom background skin image and its adjustment settings"""

    def __init__(self, skin_dir: str = "/home/pi/Development/TouchPlayer/cache/skin"):
        self.skin_dir = Path(skin_dir)
        self.skin_dir.mkdir(parents=True, exist_ok=True)
        self.image_path = self.skin_dir / "background.jpg"
        self.settings_path = self.skin_dir / "settings.json"

    def _read_settings(self) -> Dict[str, Any]:
        if not self.settings_path.exists():
            return dict(DEFAULT_SETTINGS)
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(stored)
            return merged
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read skin settings, using defaults: {e}")
            return dict(DEFAULT_SETTINGS)

    def _write_settings(self, settings: Dict[str, Any]):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f)

    def get_skin(self) -> Dict[str, Any]:
        """Get current skin state: whether an image is set plus its settings"""
        return {
            "has_image": self.image_path.exists(),
            "settings": self._read_settings(),
        }

    def save_image(self, content_type: Optional[str], data: bytes) -> Dict[str, Any]:
        """Validate, resize, and persist an uploaded skin image"""
        if content_type not in ALLOWED_CONTENT_TYPES:
            return {"error": "Unsupported image type. Use JPEG, PNG, or WebP."}

        try:
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(data))
            image.verify()
            # Re-open after verify(), which leaves the file unusable for further ops.
            image = Image.open(io.BytesIO(data))
            if image.mode != "RGB":
                image = image.convert("RGB")

            width, height = image.size
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

            image.save(self.image_path, format="JPEG", quality=90)
        except Exception as e:
            logger.error(f"Failed to process skin image: {e}")
            return {"error": "Could not process image file."}

        return {"success": True}

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update one or more adjustment values"""
        settings = self._read_settings()
        for key, value in updates.items():
            if key in DEFAULT_SETTINGS and value is not None:
                settings[key] = value
        self._write_settings(settings)
        return {"success": True, "settings": settings}

    def remove_skin(self) -> Dict[str, Any]:
        """Remove the skin image and reset settings"""
        if self.image_path.exists():
            os.remove(self.image_path)
        if self.settings_path.exists():
            os.remove(self.settings_path)
        return {"success": True}


# Global instance
skin_manager = SkinManager()
