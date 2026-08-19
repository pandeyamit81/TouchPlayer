"""
TouchPlayer Settings API Routes
System settings endpoints
"""
from typing import Optional
import asyncio
from datetime import datetime
import os
import shutil
import subprocess
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_session
from app.services.mpd_service import mpd_service
from app.services.library.scanner import get_scan_dirs, run_scan
from app.database.models import ScanState

router = APIRouter()
scan_task: Optional[asyncio.Task] = None


def _run_scan_sync(full_scan: bool) -> None:
    asyncio.run(run_scan(full_scan=full_scan))


async def _run_scan_in_background(full_scan: bool) -> None:
    """Run the blocking scanner away from FastAPI's event loop."""
    try:
        await asyncio.to_thread(_run_scan_sync, full_scan)
    except Exception as e:
        logger.error(f"Background media scan failed: {e}")


def _read_memory() -> dict:
    values = {}
    with open("/proc/meminfo", encoding="utf-8") as meminfo:
        for line in meminfo:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", values.get("MemFree", 0))
    used = max(0, total - available)
    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "percent": round((used / total) * 100, 1) if total else 0,
    }


def _read_temperature() -> Optional[float]:
    thermal_root = "/sys/class/thermal"
    try:
        for entry in os.listdir(thermal_root):
            path = os.path.join(thermal_root, entry, "temp")
            if os.path.isfile(path):
                return round(int(open(path, encoding="utf-8").read().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None
    return None


@router.get("/settings/system")
async def get_system_settings():
    """Get system settings"""
    return {
        "media_dirs": get_scan_dirs(),
        "supported_extensions": [".mp3", ".flac", ".wav", ".aac", ".ogg", ".oga", ".wma", ".m4a", ".m4b", ".opus", ".webm", ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv"],
        "artwork_cache_dir": "/home/pi/Development/TouchPlayer/cache/artwork",
        "database_path": "/home/pi/Development/TouchPlayer/cache/touchplayer.db",
    }


@router.post("/settings/scan")
async def start_scan(full_scan: bool = False):
    """Start media library scan"""
    global scan_task
    if scan_task and not scan_task.done():
        return JSONResponse(status_code=409, content={"success": False, "message": "A media scan is already running"})

    scan_task = asyncio.create_task(_run_scan_in_background(full_scan))
    return JSONResponse(status_code=202, content={"success": True, "status": "started"})


@router.get("/settings/scan/status")
async def get_scan_status(db: Session = Depends(get_session)):
    """Get scan status"""
    scan_states = db.query(ScanState).all()
    scan_state = max(scan_states, key=lambda state: state.started_at or datetime.min, default=None)
    if not scan_state:
        return {
            "status": "idle",
            "progress": 0,
            "total_files": 0,
            "processed_files": 0,
        }

    return {
        "status": scan_state.status,
        "progress": round((scan_state.processed_files / scan_state.total_files) * 100) if scan_state.total_files else 0,
        "total_files": scan_state.total_files,
        "processed_files": scan_state.processed_files,
        "new_files": scan_state.new_files,
        "modified_files": scan_state.modified_files,
        "deleted_files": scan_state.deleted_files,
        "error": scan_state.error,
        "started_at": scan_state.started_at,
        "completed_at": scan_state.completed_at,
    }


@router.get("/settings/performance")
async def get_system_performance():
    """Get live system performance metrics for the touchscreen dashboard."""
    memory = _read_memory()
    storage = shutil.disk_usage("/")
    load_1, load_5, load_15 = os.getloadavg()
    uptime = 0
    try:
        with open("/proc/uptime", encoding="utf-8") as uptime_file:
            uptime = float(uptime_file.read().split()[0])
    except (OSError, ValueError):
        pass
    return {
        "memory": memory,
        "storage": {
            "total_bytes": storage.total,
            "used_bytes": storage.used,
            "free_bytes": storage.free,
            "percent": round((storage.used / storage.total) * 100, 1) if storage.total else 0,
        },
        "temperature_c": _read_temperature(),
        "load": {"one_minute": load_1, "five_minutes": load_5, "fifteen_minutes": load_15},
        "uptime_seconds": round(uptime),
        "processes": len(os.listdir("/proc")),
        "timestamp": time.time(),
    }


@router.post("/settings/mpd/update")
async def update_mpd_database():
    """Update MPD database"""
    try:
        result = await mpd_service.update()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to update MPD database: {e}")


@router.post("/settings/mpd/rescan")
async def rescan_mpd_database():
    """Rescan MPD database"""
    try:
        result = await mpd_service.rescan()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to rescan MPD database: {e}")


@router.get("/settings/mpd/status")
async def get_mpd_status():
    """Get MPD status"""
    try:
        status = await mpd_service.status()
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MPD connection failed: {e}")


@router.post("/settings/restart")
async def restart_service():
    """Restart TouchPlayer service"""
    import os
    import signal
    
    # This would be called via systemd
    os.kill(os.getpid(), signal.SIGTERM)
    
    return {"success": True, "message": "Service restart initiated"}


def _schedule_power_action(action: str) -> None:
    """Start a privileged power action without waiting for the machine to stop."""
    subprocess.Popen(
        ["sudo", "-n", "systemctl", action],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


@router.post("/settings/power/reboot")
async def reboot_raspberry_pi():
    """Reboot the Raspberry Pi after returning an acknowledgement."""
    try:
        _schedule_power_action("reboot")
        return {"success": True, "message": "Raspberry Pi reboot scheduled"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to schedule reboot: {e}")


@router.post("/settings/power/shutdown")
async def shutdown_raspberry_pi():
    """Power off the Raspberry Pi after returning an acknowledgement."""
    try:
        _schedule_power_action("poweroff")
        return {"success": True, "message": "Raspberry Pi shutdown scheduled"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to schedule shutdown: {e}")
