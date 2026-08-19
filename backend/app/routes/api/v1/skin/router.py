"""
TouchPlayer Skin API Routes
Custom background skin upload and adjustment endpoints
"""
from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.skin.manager import skin_manager

router = APIRouter()

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


class SkinSettingsUpdate(BaseModel):
    fit: Optional[str] = None
    opacity: Optional[float] = None
    blur: Optional[float] = None
    brightness: Optional[float] = None
    overlay_color: Optional[str] = None
    overlay_opacity: Optional[float] = None


@router.get("/skin")
async def get_skin():
    """Get current skin state and adjustment settings"""
    return skin_manager.get_skin()


@router.post("/skin/upload")
async def upload_skin(file: UploadFile = File(...)):
    """Upload a new background skin image"""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 15 MB or smaller")

    result = skin_manager.save_image(file.content_type, data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "skin": skin_manager.get_skin()}


@router.put("/skin/settings")
async def update_skin_settings(update: SkinSettingsUpdate):
    """Update skin display adjustments (fit, opacity, blur, brightness, overlay)"""
    if update.fit is not None and update.fit not in ("cover", "contain", "repeat"):
        raise HTTPException(status_code=400, detail="fit must be cover, contain, or repeat")
    for field in ("opacity", "brightness", "overlay_opacity"):
        value = getattr(update, field)
        if value is not None and not (0 <= value <= 2):
            raise HTTPException(status_code=400, detail=f"{field} must be between 0 and 2")
    if update.blur is not None and not (0 <= update.blur <= 20):
        raise HTTPException(status_code=400, detail="blur must be between 0 and 20")

    result = skin_manager.update_settings(update.model_dump(exclude_unset=True))
    return result


@router.delete("/skin")
async def remove_skin():
    """Remove the current skin image and reset adjustments"""
    return skin_manager.remove_skin()


@router.get("/skin/image")
async def get_skin_image():
    """Serve the current skin background image"""
    if not skin_manager.image_path.exists():
        raise HTTPException(status_code=404, detail="No skin image set")
    return FileResponse(
        skin_manager.image_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
