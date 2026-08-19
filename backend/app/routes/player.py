from fastapi import APIRouter
from mpd import MPDClient
router=APIRouter(prefix="/api/v1/player")
@router.get("/status")
def status():
 c=MPDClient(); c.connect("localhost",6600); s=c.status(); c.close(); c.disconnect(); return s
