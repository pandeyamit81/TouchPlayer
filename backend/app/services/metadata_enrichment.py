"""MusicBrainz metadata enrichment for incomplete local track tags."""
import json
import os
import socket
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from loguru import logger


class MusicBrainzClient:
    """Small, rate-limited client for public MusicBrainz metadata."""

    def __init__(self):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.user_agent = os.environ.get(
            "TOUCHPLAYER_METADATA_USER_AGENT",
            "TouchPlayer/1.0 (local Raspberry Pi music player)",
        )
        self._lock = threading.Lock()
        self._last_request = 0.0

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            wait = 1.05 - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            query = "&".join(f"{key}={quote_plus(str(value))}" for key, value in params.items())
            request = Request(
                f"{self.base_url}/{path}?{query}",
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._last_request = time.monotonic()
            return payload

    def is_available(self) -> bool:
        """Check service reachability before attempting a metadata lookup."""
        host = urlparse(self.base_url).hostname
        if not host:
            return False
        try:
            with socket.create_connection((host, 443), timeout=2):
                return True
        except OSError:
            return False

    def _composer_from_relations(self, relations: list[Dict[str, Any]]) -> Optional[str]:
        names = []
        for relation in relations:
            relation_type = str(relation.get("type", "")).lower()
            target = relation.get("artist") or relation.get("target") or {}
            if relation_type in {"composer", "writer", "lyricist"} and isinstance(target, dict):
                name = target.get("name") or target.get("sort-name")
                if name:
                    names.append(name)
        return ", ".join(dict.fromkeys(names)) or None

    def lookup(self, title: str, artist: str = "", album: str = "") -> Dict[str, Any]:
        terms = [f'recording:"{title}"']
        if artist and not artist.lower().startswith("unknown"):
            terms.append(f'artist:"{artist}"')
        if album and not album.lower().startswith("unknown"):
            terms.append(f'release:"{album}"')
        search = self._get("recording", {"query": " AND ".join(terms), "fmt": "json", "limit": 5})
        recordings = search.get("recordings") or []
        if not recordings:
            return {}

        recording = recordings[0]
        result: Dict[str, Any] = {"source": "musicbrainz", "source_id": recording.get("id")}
        credits = recording.get("artist-credit") or []
        artist_names = [item.get("name") or item.get("artist", {}).get("name") for item in credits]
        artist_names = [name for name in artist_names if name]
        releases = recording.get("releases") or []
        release = releases[0] if releases else {}
        if recording.get("title"):
            result["title"] = recording["title"]
        if artist_names:
            result["artist"] = ", ".join(dict.fromkeys(artist_names))
        if release.get("title"):
            result["album"] = release["title"]
        date = release.get("date") or recording.get("first-release-date")
        if date and str(date)[:4].isdigit():
            result["year"] = int(str(date)[:4])

        tags = recording.get("genres") or recording.get("tags") or []
        if tags:
            result["genre"] = max(tags, key=lambda tag: tag.get("count", 0)).get("name")

        details = self._get(
            f"recording/{recording['id']}",
            {"inc": "artist-credits+releases+genres+tags+work-rels", "fmt": "json"},
        )
        composer = self._composer_from_relations(details.get("relations") or [])
        if not composer:
            for relation in details.get("relations") or []:
                work = relation.get("work")
                if not work or not work.get("id"):
                    continue
                work_details = self._get(
                    f"work/{work['id']}",
                    {"inc": "artist-rels", "fmt": "json"},
                )
                composer = self._composer_from_relations(work_details.get("relations") or [])
                if composer:
                    break
        if composer:
            result["composer"] = composer
        return result


musicbrainz_client = MusicBrainzClient()
