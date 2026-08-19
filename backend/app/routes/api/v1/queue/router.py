"""
TouchPlayer Queue API Routes
Queue management endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models import Track, QueueItem
from app.services.queue.manager import queue_manager

router = APIRouter()


@router.get("/queue")
async def get_queue(db: Session = Depends(get_session)):
    """Get current queue"""
    return await queue_manager.get_queue_with_status(db)


@router.post("/queue/add")
async def add_to_queue(
    track_id: int,
    position: Optional[int] = None,
    db: Session = Depends(get_session),
):
    """Add track to queue"""
    result = await queue_manager.add_to_queue(db, track_id, position)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/queue/add-next")
async def add_next_to_queue(track_id: int, db: Session = Depends(get_session)):
    """Add a track immediately after the currently playing queue item."""
    result = await queue_manager.add_to_queue(db, track_id, position=1, added_by="next")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/queue/remove")
async def remove_from_queue(
    position: Optional[int] = None,
    track_id: Optional[int] = None,
    db: Session = Depends(get_session),
):
    """Remove track from queue"""
    result = await queue_manager.remove_from_queue(db, position, track_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/queue/clear")
async def clear_queue(db: Session = Depends(get_session)):
    """Clear queue"""
    return await queue_manager.clear_queue(db)


@router.post("/queue/move")
async def move_in_queue(
    from_position: int,
    to_position: int,
    db: Session = Depends(get_session),
):
    """Move track in queue"""
    result = await queue_manager.move_in_queue(db, from_position, to_position)
    return result


@router.post("/queue/swap")
async def swap_in_queue(
    pos1: int,
    pos2: int,
    db: Session = Depends(get_session),
):
    """Swap two tracks in queue"""
    result = await queue_manager.swap_in_queue(db, pos1, pos2)
    return result


@router.post("/queue/play/{track_id}")
async def play_track(track_id: int, db: Session = Depends(get_session)):
    """Play a specific track"""
    result = await queue_manager.play_track(db, track_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/queue/play/position/{position}")
async def play_queue_position(position: int, db: Session = Depends(get_session)):
    """Play track at specific position"""
    result = await queue_manager.play_queue_position(db, position)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
