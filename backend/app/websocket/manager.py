"""
TouchPlayer WebSocket Manager
Manages WebSocket connections for real-time updates
"""
from typing import List, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import asyncio


class WebSocketManager:
    """WebSocket manager for real-time updates"""
    
    def __init__(self):
        self.connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, ws: WebSocket):
        """Connect a new WebSocket client"""
        async with self._lock:
            await ws.accept()
            self.connections.append(ws)
            logger.info(f"WebSocket client connected. Total connections: {len(self.connections)}")
    
    def disconnect(self, ws: WebSocket):
        """Disconnect a WebSocket client"""
        if ws in self.connections:
            self.connections.remove(ws)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self.connections)}")
    
    async def broadcast(self, msg: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        async with self._lock:
            dead = []
            for client in self.connections:
                try:
                    await client.send_json(msg)
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {e}")
                    dead.append(client)
            
            for client in dead:
                self.disconnect(client)
    
    async def broadcast_player_event(self, events: List[str], status: Dict[str, Any], song: Dict[str, Any]):
        """Broadcast player event"""
        payload = {
            "type": "player_event",
            "events": events,
            "status": status,
            "song": song,
        }
        await self.broadcast(payload)
    
    async def broadcast_queue_update(self, queue: List[Dict[str, Any]], status: Dict[str, Any]):
        """Broadcast queue update"""
        payload = {
            "type": "queue_update",
            "queue": queue,
            "status": status,
        }
        await self.broadcast(payload)
    
    async def broadcast_playlist_update(self, playlist: Dict[str, Any]):
        """Broadcast playlist update"""
        payload = {
            "type": "playlist_update",
            "playlist": playlist,
        }
        await self.broadcast(payload)
    
    async def broadcast_library_update(self, stats: Dict[str, int]):
        """Broadcast library update"""
        payload = {
            "type": "library_update",
            "stats": stats,
        }
        await self.broadcast(payload)
    
    async def broadcast_volume_change(self, volume: int):
        """Broadcast volume change"""
        payload = {
            "type": "volume_change",
            "volume": volume,
        }
        await self.broadcast(payload)
    
    async def broadcast_playback_state(self, state: Dict[str, Any]):
        """Broadcast playback state"""
        payload = {
            "type": "playback_state",
            "state": state,
        }
        await self.broadcast(payload)
    
    def get_connection_count(self) -> int:
        """Get number of connected clients"""
        return len(self.connections)


# Global instance
ws_manager = WebSocketManager()
