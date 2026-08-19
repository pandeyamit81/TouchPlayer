"""
TouchPlayer MPD Event Listener
Listens for MPD events and broadcasts to WebSocket clients
"""
import asyncio
from mpd import MPDClient
from loguru import logger
from typing import List, Dict, Any

from app.websocket.manager import ws_manager


class MPDEventListener:
    """MPD event listener for real-time updates"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6600,
        password: str = None,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._running = False
        self._client: MPDClient = None
    
    def create_client(self) -> MPDClient:
        """Create MPD client connection"""
        client = MPDClient()
        client.timeout = self.timeout
        client.idletimeout = None
        client.connect(self.host, self.port)
        if self.password:
            client.password(self.password)
        return client
    
    async def run(self):
        """Run the event listener"""
        self._running = True
        
        while self._running:
            try:
                client = self.create_client()
                logger.info("MPD event listener connected")
                
                while self._running:
                    # Wait for MPD events
                    events: List[str] = client.idle("player", "playlist", "mixer", "options")
                    
                    # Get current status
                    status = client.status()
                    song = client.currentsong()
                    
                    # Broadcast event
                    await ws_manager.broadcast_player_event(events, status, song)
                    
                    # Close and reopen client to avoid timeout issues
                    client.close()
                    client.disconnect()
                    client = self.create_client()
                    
            except asyncio.CancelledError:
                logger.info("MPD event listener cancelled")
                break
                
            except Exception as e:
                logger.error(f"MPD event listener error: {e}")
                await asyncio.sleep(5)  # Wait before reconnecting
                
            finally:
                if self._client:
                    try:
                        self._client.close()
                        self._client.disconnect()
                    except Exception:
                        pass
    
    async def stop(self):
        """Stop the event listener"""
        self._running = False
    
    async def __aenter__(self):
        await self.run()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


# Global instance
mpd_event_listener = MPDEventListener()
