"""
TouchPlayer Queue Models
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class QueueItem(BaseModel):
    """Queue item model"""
    id: int
    track_id: int
    position: int
    added_at: datetime
    added_by: Optional[str] = None
