"""
TouchPlayer Samba API Routes
Network file share configuration endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import os

from app.services.samba.manager import samba_manager
from app.services.library.scanner import DEFAULT_MEDIA_DIRS, run_scan

router = APIRouter()


class SambaShareRequest(BaseModel):
    name: str
    path: str
    read_only: bool = False
    guest_ok: bool = True


@router.get("/samba")
async def get_samba_share():
    """Get the current Samba share configuration and service status"""
    return {
        "active": samba_manager.is_active(),
        "share": samba_manager.get_share(),
    }


@router.post("/samba")
async def configure_samba_share(request: SambaShareRequest):
    """Create or replace the shared folder exposed over Samba"""
    result = samba_manager.apply_share(
        request.name, request.path, request.read_only, request.guest_ok
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    scan_dirs = DEFAULT_MEDIA_DIRS + [os.path.abspath(request.path)]
    try:
        result["scan"] = await run_scan(media_dirs=list(dict.fromkeys(scan_dirs)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Share configured but scan failed: {e}")
    return result


@router.delete("/samba")
async def remove_samba_share():
    """Remove the shared folder"""
    share = samba_manager.get_share()
    result = samba_manager.remove_share()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    if share and share.get("path"):
        try:
            result["scan"] = await run_scan(media_dirs=DEFAULT_MEDIA_DIRS.copy())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Share removed but library cleanup failed: {e}")
    return result


@router.get("/samba/files")
async def list_samba_files(subpath: str = Query("", alias="path")):
    """List the shared folder's contents with permissions, owner, and size"""
    result = samba_manager.list_files(subpath)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

