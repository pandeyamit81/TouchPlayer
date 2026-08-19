"""
TouchPlayer Routes Package
"""
from .api.v1.music import router as music_router
from .api.v1.playlists import router as playlists_router
from .api.v1.queue import router as queue_router
from .api.v1.playback import router as playback_router
from .api.v1.artwork import router as artwork_router
from .api.v1.settings import router as settings_router
from .api.v1.bluetooth import router as bluetooth_router
from .api.v1.wifi import router as wifi_router

__all__ = [
    "music_router",
    "playlists_router",
    "queue_router",
    "playback_router",
    "artwork_router",
    "settings_router",
    "bluetooth_router",
    "wifi_router",
]
