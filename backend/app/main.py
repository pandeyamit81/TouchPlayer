"""
TouchPlayer Main Application
FastAPI backend for Raspberry Pi touchscreen media player
"""
import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.routes.api.v1.music import router as music_router
from app.routes.api.v1.playlists import router as playlists_router
from app.routes.api.v1.queue import router as queue_router
from app.routes.api.v1.playback import router as playback_router
from app.routes.api.v1.artwork import router as artwork_router
from app.routes.api.v1.settings import router as settings_router
from app.routes.api.v1.bluetooth import router as bluetooth_router
from app.routes.api.v1.wifi import router as wifi_router
from app.routes.api.v1.skin import router as skin_router
from app.routes.api.v1.samba import router as samba_router
from app.routes.api.v1.sms import router as sms_router
from app.websocket.manager import ws_manager
from app.services.mpd_event_listener import mpd_event_listener
from app.database.session import init_db


# Create FastAPI app
app = FastAPI(
    title="TouchPlayer API",
    description="Touchscreen media player API for Raspberry Pi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize application on startup"""
    logger.info("Starting TouchPlayer...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # MPD event listener will be started separately
    logger.info("MPD event listener will be started separately")
    
    logger.info("TouchPlayer started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down TouchPlayer...")
    
    # Stop MPD event listener
    await mpd_event_listener.stop()
    logger.info("MPD event listener stopped")
    
    logger.info("TouchPlayer shutdown complete")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "running",
        "phase": "2A",
        "version": "1.0.0",
        "websocket_connections": ws_manager.get_connection_count(),
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Include routers
app.include_router(music_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")
app.include_router(playback_router, prefix="/api/v1")
app.include_router(artwork_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(bluetooth_router, prefix="/api/v1")
app.include_router(wifi_router, prefix="/api/v1")
app.include_router(skin_router, prefix="/api/v1")
app.include_router(samba_router, prefix="/api/v1")
app.include_router(sms_router, prefix="/api/v1")

# WebSocket endpoint
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ws_manager

ws_router = APIRouter()


@ws_router.websocket("/ws/player")
async def websocket_player_endpoint(websocket: WebSocket):
    """WebSocket endpoint for player events"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


app.include_router(ws_router)
