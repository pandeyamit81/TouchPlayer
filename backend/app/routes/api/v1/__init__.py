"""
TouchPlayer API Routes Package
"""
from .music import router as music_router
from .playlists import router as playlists_router
from .queue import router as queue_router
from .playback import router as playback_router
from .artwork import router as artwork_router
from .settings import router as settings_router
from .bluetooth import router as bluetooth_router
from .wifi import router as wifi_router
from .skin import router as skin_router
from .samba import router as samba_router
from .sms import router as sms_router

__all__ = [
    "music_router",
    "playlists_router",
    "queue_router",
    "playback_router",
    "artwork_router",
    "settings_router",
    "bluetooth_router",
    "wifi_router",
    "skin_router",
    "samba_router",
    "sms_router",
]
