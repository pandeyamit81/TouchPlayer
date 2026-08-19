"""
TouchPlayer MPD Service
Provides comprehensive MPD client functionality
"""
import asyncio
from typing import Optional, List, Dict, Any
from mpd import MPDClient
from loguru import logger
import time


class MPDService:
    """MPD service for controlling playback"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6600,
        password: Optional[str] = None,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._client: Optional[MPDClient] = None
        self._lock = asyncio.Lock()
    
    def _get_client(self) -> MPDClient:
        """Get MPD client connection"""
        if self._client is None:
            self._client = MPDClient()
            self._client.timeout = self.timeout
            self._client.idletimeout = None
            self._client.connect(self.host, self.port)
            if self.password:
                self._client.password(self.password)
        return self._client
    
    def _close_client(self):
        """Close MPD client connection"""
        if self._client is not None:
            try:
                self._client.close()
                self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error closing MPD client: {e}")
            finally:
                self._client = None
    
    async def _execute(self, func, *args, **kwargs):
        """Execute MPD command with reconnection logic"""
        async with self._lock:
            client = self._get_client()
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, lambda: func(client, *args, **kwargs)
                )
            except Exception as e:
                logger.error(f"MPD command failed: {e}")
                self._close_client()
                raise
    
    # Playback control
    async def play(self, song_id: Optional[int] = None) -> Dict[str, Any]:
        """Start playback"""
        return await self._execute(lambda c: c.play(song_id) if song_id is not None else c.play())
    
    async def pause(self, pause: bool = True) -> Dict[str, Any]:
        """Pause/resume playback"""
        return await self._execute(lambda c: c.pause(1 if pause else 0))
    
    async def stop(self) -> Dict[str, Any]:
        """Stop playback"""
        return await self._execute(lambda c: c.stop())
    
    async def next(self) -> Dict[str, Any]:
        """Skip to next track"""
        return await self._execute(lambda c: c.next())
    
    async def previous(self) -> Dict[str, Any]:
        """Go to previous track"""
        return await self._execute(lambda c: c.previous())
    
    async def seek(self, song_id: int, time_pos: int) -> Dict[str, Any]:
        """Seek to position in track"""
        return await self._execute(lambda c: c.seek(song_id, time_pos))
    
    async def seekid(self, song_id: int, time_pos: int) -> Dict[str, Any]:
        """Seek to position by song ID"""
        return await self._execute(lambda c: c.seekid(song_id, time_pos))
    
    # Volume control
    async def set_volume(self, volume: int) -> Dict[str, Any]:
        """Set volume (0-100)"""
        return await self._execute(lambda c: c.setvol(volume))
    
    async def volume_up(self, step: int = 5) -> Dict[str, Any]:
        """Increase volume"""
        status = await self.status()
        current_volume = int(status.get("volume", 0))
        new_volume = min(100, current_volume + step)
        return await self.set_volume(new_volume)
    
    async def volume_down(self, step: int = 5) -> Dict[str, Any]:
        """Decrease volume"""
        status = await self.status()
        current_volume = int(status.get("volume", 0))
        new_volume = max(0, current_volume - step)
        return await self.set_volume(new_volume)
    
    # Playback modes
    async def set_repeat(self, repeat: bool) -> Dict[str, Any]:
        """Enable/disable repeat mode"""
        return await self._execute(lambda c: c.repeat(1 if repeat else 0))
    
    async def set_random(self, random: bool) -> Dict[str, Any]:
        """Enable/disable random mode"""
        return await self._execute(lambda c: c.random(1 if random else 0))
    
    async def set_single(self, single: bool) -> Dict[str, Any]:
        """Enable/disable single mode"""
        return await self._execute(lambda c: c.single(1 if single else 0))
    
    async def set_crossfade(self, crossfade: int) -> Dict[str, Any]:
        """Set crossfade duration in seconds"""
        return await self._execute(lambda c: c.crossfade(crossfade))
    
    async def set_consume(self, consume: bool) -> Dict[str, Any]:
        """Enable/disable consume mode"""
        return await self._execute(lambda c: c.consume(1 if consume else 0))
    
    # Queue management
    async def add(self, uri: str) -> Dict[str, Any]:
        """Add track to queue"""
        return await self._execute(lambda c: c.add(uri))
    
    async def addid(self, uri: str) -> Dict[str, Any]:
        """Add track to queue and return its ID"""
        return await self._execute(lambda c: c.addid(uri))
    
    async def delete(self, song_pos: int) -> Dict[str, Any]:
        """Delete track from queue by position"""
        return await self._execute(lambda c: c.delete(song_pos))
    
    async def deleteid(self, song_id: int) -> Dict[str, Any]:
        """Delete track from queue by ID"""
        return await self._execute(lambda c: c.deleteid(song_id))
    
    async def move(self, from_pos: int, to_pos: int) -> Dict[str, Any]:
        """Move track in queue"""
        return await self._execute(lambda c: c.move(from_pos, to_pos))
    
    async def moveid(self, from_id: int, to_pos: int) -> Dict[str, Any]:
        """Move track in queue by ID"""
        return await self._execute(lambda c: c.moveid(from_id, to_pos))
    
    async def swap(self, pos1: int, pos2: int) -> Dict[str, Any]:
        """Swap two tracks in queue"""
        return await self._execute(lambda c: c.swap(pos1, pos2))
    
    async def swapid(self, id1: int, id2: int) -> Dict[str, Any]:
        """Swap two tracks in queue by ID"""
        return await self._execute(lambda c: c.swapid(id1, id2))
    
    async def clear(self) -> Dict[str, Any]:
        """Clear queue"""
        return await self._execute(lambda c: c.clear())
    
    async def playlistinfo(self, song_pos: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get queue information"""
        return await self._execute(lambda c: c.playlistinfo(song_pos))
    
    async def playlistid(self, song_id: int) -> List[Dict[str, Any]]:
        """Get queue information by song ID"""
        return await self._execute(lambda c: c.playlistid(song_id))
    
    async def playlistfind(
        self, tag: str, needle: str
    ) -> List[Dict[str, Any]]:
        """Find tracks in queue"""
        return await self._execute(lambda c: c.playlistfind(tag, needle))
    
    async def playlistsearch(
        self, tag: str, needle: str
    ) -> List[Dict[str, Any]]:
        """Search tracks in queue"""
        return await self._execute(lambda c: c.playlistsearch(tag, needle))
    
    async def plchanges(self, version: int) -> List[Dict[str, Any]]:
        """Get playlist changes since version"""
        return await self._execute(lambda c: c.plchanges(version))
    
    async def plchangesposid(self, version: int) -> List[Dict[str, Any]]:
        """Get playlist changes with positions"""
        return await self._execute(lambda c: c.plchangesposid(version))
    
    # Playlist management
    async def playlistload(self, playlist: str, start: int = 0, end: int = -1) -> Dict[str, Any]:
        """Load playlist into queue"""
        return await self._execute(lambda c: c.playlistload(playlist, start, end))
    
    async def playlistadd(self, playlist: str, uri: str) -> Dict[str, Any]:
        """Add track to playlist"""
        return await self._execute(lambda c: c.playlistadd(playlist, uri))
    
    async def playlistdelete(self, playlist: str, song_pos: int) -> Dict[str, Any]:
        """Delete track from playlist"""
        return await self._execute(lambda c: c.playlistdelete(playlist, song_pos))
    
    async def playlistmove(self, playlist: str, from_pos: int, to_pos: int) -> Dict[str, Any]:
        """Move track in playlist"""
        return await self._execute(lambda c: c.playlistmove(playlist, from_pos, to_pos))
    
    async def listplaylists(self) -> List[Dict[str, Any]]:
        """List all playlists"""
        return await self._execute(lambda c: c.listplaylists())
    
    async def playlistinfo(self, playlist: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get playlist information"""
        return await self._execute(lambda c: c.playlistinfo(playlist))
    
    async def save(self, name: str) -> Dict[str, Any]:
        """Save current queue as playlist"""
        return await self._execute(lambda c: c.save(name))
    
    async def load(self, name: str) -> Dict[str, Any]:
        """Load playlist into queue"""
        return await self._execute(lambda c: c.load(name))
    
    async def deleteplaylist(self, name: str) -> Dict[str, Any]:
        """Delete playlist"""
        return await self._execute(lambda c: c.deleteplaylist(name))
    
    async def renameplaylist(self, name: str, new_name: str) -> Dict[str, Any]:
        """Rename playlist"""
        return await self._execute(lambda c: c.renameplaylist(name, new_name))
    
    # Status information
    async def status(self) -> Dict[str, Any]:
        """Get player status"""
        return await self._execute(lambda c: c.status())
    
    async def currentsong(self) -> Dict[str, Any]:
        """Get current playing song"""
        return await self._execute(lambda c: c.currentsong())
    
    async def stats(self) -> Dict[str, Any]:
        """Get player statistics"""
        return await self._execute(lambda c: c.stats())
    
    async def count(self, tag: str, query: str = "") -> Dict[str, Any]:
        """Count tracks matching query"""
        return await self._execute(lambda c: c.count(tag, query))
    
    async def search(
        self, tag: str, query: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search library"""
        return await self._execute(lambda c: c.search(tag, query, offset, limit))
    
    async def find(
        self, tag: str, query: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find tracks in library (exact match)"""
        return await self._execute(lambda c: c.find(tag, query, offset, limit))
    
    async def searchadd(
        self, tag: str, query: str
    ) -> Dict[str, Any]:
        """Search and add matching tracks to queue"""
        return await self._execute(lambda c: c.searchadd(tag, query))
    
    async def searchaddpl(
        self, name: str, tag: str, query: str
    ) -> Dict[str, Any]:
        """Search and add to playlist"""
        return await self._execute(lambda c: c.searchaddpl(name, tag, query))
    
    # Library browsing
    async def list(
        self, tag: str, query: str = "", sort: str = ""
    ) -> List[str]:
        """List all values for a tag"""
        return await self._execute(lambda c: c.list(tag, query, sort))
    
    async def lsinfo(self, uri: str = "") -> List[Dict[str, Any]]:
        """List directory information"""
        return await self._execute(lambda c: c.lsinfo(uri))
    
    async def listfiles(self, uri: str = "") -> List[Dict[str, Any]]:
        """List files in directory"""
        return await self._execute(lambda c: c.listfiles(uri))
    
    async def listall(self, uri: str = "") -> List[Dict[str, Any]]:
        """List all files and directories"""
        return await self._execute(lambda c: c.listall(uri))
    
    async def listallinfo(self, uri: str = "") -> List[Dict[str, Any]]:
        """List all files with metadata"""
        return await self._execute(lambda c: c.listallinfo(uri))
    
    async def findadd(
        self, tag: str, query: str
    ) -> Dict[str, Any]:
        """Find and add to queue"""
        return await self._execute(lambda c: c.findadd(tag, query))
    
    async def addid(self, uri: str) -> int:
        """Add track to queue and return its ID"""
        return await self._execute(lambda c: c.addid(uri))
    
    async def random(self, state: int = 1) -> Dict[str, Any]:
        """Toggle random mode"""
        return await self._execute(lambda c: c.random(state))
    
    async def repeat(self, state: int = 1) -> Dict[str, Any]:
        """Toggle repeat mode"""
        return await self._execute(lambda c: c.repeat(state))
    
    async def single(self, state: int = 1) -> Dict[str, Any]:
        """Toggle single mode"""
        return await self._execute(lambda c: c.single(state))
    
    async def consume(self, state: int = 1) -> Dict[str, Any]:
        """Toggle consume mode"""
        return await self._execute(lambda c: c.consume(state))
    
    async def crossfade(self, seconds: int) -> Dict[str, Any]:
        """Set crossfade duration"""
        return await self._execute(lambda c: c.crossfade(seconds))
    
    async def mixrampdb(self, db: float) -> Dict[str, Any]:
        """Set MixRamp database threshold"""
        return await self._execute(lambda c: c.mixrampdb(db))
    
    async def mixrampdelay(self, seconds: float) -> Dict[str, Any]:
        """Set MixRamp delay"""
        return await self._execute(lambda c: c.mixrampdelay(seconds))
    
    async def replay_gain_mode(self, mode: str) -> Dict[str, Any]:
        """Set replay gain mode"""
        return await self._execute(lambda c: c.replay_gain_mode(mode))
    
    async def replay_gain_status(self) -> Dict[str, Any]:
        """Get replay gain status"""
        return await self._execute(lambda c: c.replay_gain_status())
    
    async def urlhandlers(self) -> List[str]:
        """List available URL handlers"""
        return await self._execute(lambda c: c.urlhandlers())
    
    async def update(self, uri: str = "") -> Dict[str, Any]:
        """Update database"""
        return await self._execute(lambda c: c.update(uri))
    
    async def rescan(self, uri: str = "") -> Dict[str, Any]:
        """Rescan database"""
        return await self._execute(lambda c: c.rescan(uri))
    
    # Connection management
    async def ping(self) -> bool:
        """Ping MPD server"""
        try:
            await self._execute(lambda c: c.ping())
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close connection"""
        async with self._lock:
            self._close_client()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Global service instance
mpd_service = MPDService()
