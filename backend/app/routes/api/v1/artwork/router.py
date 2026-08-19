"""
TouchPlayer Artwork API Routes
Artwork serving endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models import Track, Album
from app.services.artwork.service import artwork_service

router = APIRouter()


@router.get("/artwork/{hash_str}")
async def get_artwork(
    hash_str: str,
    size: int = Query(256, ge=64, le=512),
    db: Session = Depends(get_session),
):
    """Get artwork by hash"""
    # Find album by hash
    from app.database.models import Album
    album = db.query(Album).filter(
        func.lower(func.replace(Album.name, " ", "")) == func.lower(func.replace(hash_str.split("_")[0], " ", ""))
    ).first()
    
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    artwork = artwork_service.get_artwork_for_album(db, album.id, size)
    
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    from fastapi.responses import Response
    return Response(content=artwork, media_type="image/jpeg")


@router.get("/artwork/track/{track_id}")
async def get_track_artwork(
    track_id: int,
    size: int = Query(256, ge=64, le=512),
    db: Session = Depends(get_session),
):
    """Get artwork for a track"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    artwork = artwork_service.get_artwork_for_track(db, track_id, size)
    
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    from fastapi.responses import Response
    return Response(content=artwork, media_type="image/jpeg")


@router.get("/artwork/album/{album_id}")
async def get_album_artwork(
    album_id: int,
    size: int = Query(256, ge=64, le=512),
    db: Session = Depends(get_session),
):
    """Get artwork for an album"""
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    artwork = artwork_service.get_artwork_for_album(db, album_id, size)
    
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    from fastapi.responses import Response
    return Response(content=artwork, media_type="image/jpeg")


@router.post("/artwork/scan")
async def scan_artwork(db: Session = Depends(get_session)):
    """Scan library for artwork"""
    stats = artwork_service.scan_library_for_artwork(db)
    return {"success": True, "stats": stats}


@router.post("/artwork/clear")
async def clear_artwork_cache():
    """Clear artwork cache"""
    artwork_service.clear_cache()
    return {"success": True}
