"""
TouchPlayer Music API Routes
Music library endpoints
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import SessionLocal, get_session
from app.database.models import Track, Album, Artist, TrackTranscript, TrackEnrichment
from app.services.mpd_service import mpd_service
from app.services.library.scanner import get_scan_dirs
from app.services.transcription import transcription_service
from app.services.metadata_enrichment import musicbrainz_client

router = APIRouter()
metadata_batch_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="metadata-enrichment")
metadata_batch_future = None
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm"}


def _songs_only(query):
    """Exclude video files from every music-library query."""
    return query.filter(*[~Track.file_path.ilike(f"%{extension}") for extension in VIDEO_EXTENSIONS])


def _missing_metadata(value: Optional[str], unknown_value: str) -> bool:
    normalized = (value or "").strip().casefold()
    return not normalized or normalized == unknown_value.casefold() or normalized.startswith("unknown ")


@router.get("/videos")
async def list_videos(
    db: Session = Depends(get_session),
    limit: int = Query(1000, ge=1, le=5000),
):
    """List scanned video files from the configured media roots."""
    tracks = db.query(Track).order_by(Track.file_path).all()
    videos = [track for track in tracks if Path(track.file_path).suffix.lower() in VIDEO_EXTENSIONS]
    return {
        "videos": [
            {
                "id": video.id,
                "file_path": video.file_path,
                "title": video.title,
                "artist": video.artist,
                "album": video.album,
                "duration": video.duration,
            }
            for video in videos[:limit]
        ],
        "media_dirs": get_scan_dirs(),
    }


@router.get("/videos/{video_id}/stream")
async def stream_video(video_id: int, db: Session = Depends(get_session)):
    """Serve a scanned video file to the browser with range support."""
    video = db.query(Track).filter(Track.id == video_id).first()
    if not video or Path(video.file_path).suffix.lower() not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Video not found")
    if not os.path.isfile(video.file_path):
        raise HTTPException(status_code=404, detail="Video file is unavailable")
    return FileResponse(video.file_path, media_type="video/" + Path(video.file_path).suffix.lower().lstrip("."))


@router.post("/music/enrich/{track_id}")
async def enrich_track(track_id: int, db: Session = Depends(get_session)):
    """Search MusicBrainz and fill only missing track metadata."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    if not musicbrainz_client.is_available():
        raise HTTPException(status_code=503, detail="Internet connection is unavailable; metadata was not changed")

    try:
        metadata = await asyncio.to_thread(
            musicbrainz_client.lookup,
            track.title,
            track.artist,
            track.album,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata lookup failed: {exc}")
    if not metadata:
        return {"track_id": track_id, "matched": False, "updated": []}

    updated = []
    new_artist = metadata.get("artist") if _missing_metadata(track.artist, "Unknown Artist") else track.artist
    new_album = metadata.get("album") if _missing_metadata(track.album, "Unknown Album") else track.album
    new_genre = metadata.get("genre") if _missing_metadata(track.genre, "Unknown Genre") else track.genre

    if new_artist and new_artist != track.artist:
        artist = db.query(Artist).filter(func.lower(Artist.name) == func.lower(new_artist)).first()
        if not artist:
            artist = Artist(name=new_artist, sort_name=new_artist)
            db.add(artist)
            db.flush()
        track.artist = new_artist
        track.artist_id = artist.id
        updated.append("artist")
    artist = track.artist_obj or db.query(Artist).filter(Artist.id == track.artist_id).first()
    if new_album and new_album != track.album:
        album = db.query(Album).filter(
            func.lower(Album.name) == func.lower(new_album),
            func.lower(Album.artist) == func.lower(track.artist),
        ).first()
        if not album:
            album = Album(name=new_album, artist=track.artist, artist_id=track.artist_id)
            db.add(album)
            db.flush()
        track.album = new_album
        track.album_id = album.id
        updated.append("album")
    if new_genre and new_genre != track.genre:
        track.genre = new_genre
        updated.append("genre")
    if track.year is None and metadata.get("year"):
        track.year = metadata["year"]
        updated.append("year")

    enrichment = db.query(TrackEnrichment).filter(TrackEnrichment.track_id == track_id).first()
    if enrichment is None:
        enrichment = TrackEnrichment(track_id=track_id)
        db.add(enrichment)
    enrichment.composer = metadata.get("composer") or enrichment.composer
    enrichment.source = metadata.get("source")
    enrichment.source_id = metadata.get("source_id")
    db.commit()
    return {
        "track_id": track_id,
        "matched": True,
        "updated": updated + (["composer"] if metadata.get("composer") else []),
        "metadata": metadata,
    }


def _run_metadata_batch(track_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for track_id in track_ids:
            try:
                asyncio.run(enrich_track(track_id, db))
            except Exception as exc:
                logger.warning(f"Batch metadata enrichment failed for track {track_id}: {exc}")
    finally:
        db.close()


@router.post("/music/enrich-missing")
async def enrich_missing_tracks(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Queue a rate-limited batch for tracks with incomplete metadata."""
    global metadata_batch_future
    if metadata_batch_future and not metadata_batch_future.done():
        raise HTTPException(status_code=409, detail="A metadata batch is already running")

    missing = db.query(Track.id).outerjoin(
        TrackEnrichment, TrackEnrichment.track_id == Track.id
    ).filter(
        or_(
            Track.artist.is_(None), Track.artist == "", Track.artist.ilike("Unknown%"),
            Track.album.is_(None), Track.album == "", Track.album.ilike("Unknown%"),
            Track.genre.is_(None), Track.genre == "", Track.genre.ilike("Unknown%"),
            TrackEnrichment.composer.is_(None), TrackEnrichment.composer == "",
        )
    ).order_by(Track.id).limit(limit).all()
    track_ids = [track_id for (track_id,) in missing]
    if not track_ids:
        return {"queued": 0, "message": "All tracks already have metadata"}

    metadata_batch_future = metadata_batch_executor.submit(_run_metadata_batch, track_ids)
    return {"queued": len(track_ids), "track_ids": track_ids, "batch_size": limit}


@router.get("/music/enrichment/{track_id}")
async def get_track_enrichment(track_id: int, db: Session = Depends(get_session)):
    """Return cached internet metadata for a track."""
    enrichment = db.query(TrackEnrichment).filter(TrackEnrichment.track_id == track_id).first()
    if not enrichment:
        return {"track_id": track_id, "composer": None, "source": None}
    return {
        "track_id": track_id,
        "composer": enrichment.composer,
        "source": enrichment.source,
        "source_id": enrichment.source_id,
        "fetched_at": enrichment.fetched_at.isoformat() if enrichment.fetched_at else None,
    }


@router.post("/music/transcribe/{track_id}")
async def transcribe_track(track_id: int, db: Session = Depends(get_session)):
    """Queue a track for background Whisper transcription."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    accepted = transcription_service.submit(track_id)
    transcript = db.query(TrackTranscript).filter(TrackTranscript.track_id == track_id).first()
    return {
        "track_id": track_id,
        "status": transcript.status if transcript else "queued",
        "accepted": accepted,
        "error": transcript.error if transcript else None,
    }


@router.get("/music/transcription/{track_id}")
async def get_track_transcription(track_id: int, db: Session = Depends(get_session)):
    """Return cached transcription status and text for a track."""
    transcript = db.query(TrackTranscript).filter(TrackTranscript.track_id == track_id).first()
    if not transcript:
        return {"track_id": track_id, "status": "not_started", "text": None, "error": None}
    return {
        "track_id": track_id,
        "status": transcript.status,
        "text": transcript.text,
        "error": transcript.error,
        "model": transcript.model,
        "updated_at": transcript.updated_at.isoformat() if transcript.updated_at else None,
    }


@router.get("/recommendations")
async def get_recommendations(
    db: Session = Depends(get_session),
    limit: int = Query(12, ge=1, le=50),
):
    """Return local song recommendations from playback and library metadata."""
    track_count = db.query(func.count(Track.id)).scalar() or 0
    if not track_count:
        return {"recommendations": [], "signals": []}

    now = datetime.utcnow()
    current_hour = datetime.now().hour
    favorite_artists = {
        artist for (artist,) in db.query(Track.artist).filter(Track.favorite.is_(True)).all()
    }
    favorite_genres = {
        genre for (genre,) in db.query(Track.genre).filter(
            Track.favorite.is_(True), Track.genre.isnot(None)
        ).all()
    }
    artist_affinity = {}
    genre_affinity = {}
    recent_album_cutoff = now - timedelta(days=14)
    recent_albums = {
        album for (album,) in db.query(Track.album).filter(
            Track.last_played >= recent_album_cutoff
        ).distinct().all()
    }
    for artist, plays in db.query(Track.artist, func.sum(func.coalesce(Track.play_count, 0))).group_by(Track.artist):
        artist_affinity[artist] = plays or 0
    for genre, plays in db.query(Track.genre, func.sum(func.coalesce(Track.play_count, 0))).filter(
        Track.genre.isnot(None)
    ).group_by(Track.genre):
        genre_affinity[genre] = plays or 0

    max_play_count = db.query(func.max(func.coalesce(Track.play_count, 0))).scalar() or 0
    score_expression = (
        case((Track.favorite.is_(True), 40), else_=0)
        + (func.coalesce(Track.rating, 0) * 6)
        + case(
            (max_play_count > 0, func.coalesce(Track.play_count, 0) * 24 / max_play_count),
            else_=0,
        )
        + case((Track.last_played.is_(None), 18), else_=0)
        + case(
            (Track.last_played.isnot(None), func.min(
                func.max(func.julianday("now") - func.julianday(Track.last_played), 0),
                30,
            ) * 0.8),
            else_=0,
        )
    ).label("score")
    candidates = db.query(Track, score_expression).order_by(score_expression.desc(), Track.title).limit(200).all()

    recommendations = []
    for track, sqlite_score in candidates:
        play_count = track.play_count or 0
        score = float(sqlite_score or 0)
        reasons = []

        if track.favorite:
            reasons.append("favorite")
        if track.rating:
            reasons.append(f"rated {track.rating}/5")
        if play_count >= 3:
            reasons.append("frequently played")

        if track.artist in favorite_artists and not track.favorite:
            reasons.append("similar artist")
        elif artist_affinity.get(track.artist, 0) > 0 and not track.favorite:
            reasons.append("artist match")
        if track.genre in favorite_genres and not track.favorite:
            reasons.append("favorite genre")
        elif track.genre and genre_affinity.get(track.genre, 0) > 0:
            reasons.append("genre match")

        if track.album in recent_albums:
            reasons.append("recent album")
        if track.last_played is None:
            reasons.append("never played")
        else:
            days_since_played = max((now - track.last_played).total_seconds() / 86400, 0)
            if days_since_played >= 14:
                reasons.append("not played recently")
            if track.last_played.hour == current_hour:
                reasons.append("played around this time")

        recommendations.append({
            "id": track.id,
            "file_path": track.file_path,
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "duration": track.duration,
            "track_number": track.track_number,
            "play_count": play_count,
            "favorite": track.favorite,
            "rating": track.rating,
            "score": round(score, 2),
            "reasons": reasons[:3] or ["library match"],
        })

    recommendations.sort(key=lambda item: (-item["score"], item["title"].casefold()))
    return {
        "recommendations": recommendations[:limit],
        "signals": [
            "frequently played",
            "favorite tracks",
            "artist and genre affinity",
            "recent albums",
            "not played recently",
            "time of day",
        ],
    }


@router.get("/music")
async def get_tracks(
    db: Session = Depends(get_session),
    artist: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get music tracks"""
    query = _songs_only(db.query(Track))
    
    if artist:
        query = query.filter(Track.artist == artist)
    if album:
        query = query.filter(Track.album == album)
    if genre:
        query = query.filter(Track.genre == genre)
    
    total = query.count()
    tracks = query.order_by(Track.added_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "tracks": [
            {
                "id": t.id,
                "file_path": t.file_path,
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "duration": t.duration,
                "track_number": t.track_number,
                "disc_number": t.disc_number,
                "year": t.year,
                "genre": t.genre,
                "play_count": t.play_count,
                "favorite": t.favorite,
                "added_at": t.added_at.isoformat(),
            }
            for t in tracks
        ],
    }


@router.get("/albums")
async def get_albums(
    db: Session = Depends(get_session),
    artist: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get albums"""
    query = _songs_only(db.query(
        Track.album.label("name"),
        Track.artist,
        func.min(Track.year).label("year"),
        func.min(Track.genre).label("genre"),
        func.count(Track.id).label("track_count"),
        func.coalesce(func.sum(Track.duration), 0).label("duration"),
    )).group_by(Track.album, Track.artist)
    if artist:
        query = query.filter(Track.artist == artist)
    if search:
        search_term = f"%{search}%"
        query = query.filter((Track.album.ilike(search_term)) | (Track.artist.ilike(search_term)))

    total = query.count()
    albums = query.order_by(Track.album, Track.artist).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "albums": [
            {
                "id": index + 1 + offset,
                "name": album.name,
                "artist": album.artist,
                "year": album.year,
                "genre": album.genre,
                "track_count": album.track_count,
                "duration": album.duration,
                "has_artwork": False,
            }
            for index, album in enumerate(albums)
        ],
    }


@router.get("/artists")
async def get_artists(
    db: Session = Depends(get_session),
    genre: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get artists"""
    query = _songs_only(db.query(
        Track.artist.label("name"),
        func.min(Track.genre).label("genre"),
        func.count(Track.id).label("track_count"),
        func.coalesce(func.sum(Track.play_count), 0).label("play_count"),
    )).group_by(Track.artist)
    if genre:
        query = query.filter(Track.genre == genre)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Track.artist.ilike(search_term) | Track.genre.ilike(search_term)
        )
    total = query.count()
    artists = query.order_by(Track.artist).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "artists": [
            {
                "id": index + 1 + offset,
                "name": artist.name,
                "sort_name": artist.name,
                "genre": artist.genre,
                "track_count": artist.track_count,
                "album_count": _songs_only(db.query(func.count(func.distinct(Track.album)))).filter(Track.artist == artist.name).scalar() or 0,
                "play_count": artist.play_count,
            }
            for index, artist in enumerate(artists)
        ],
    }


@router.get("/music/search")
async def search_music(
    db: Session = Depends(get_session),
    query: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=1000),
    deep: bool = False,
):
    """Search metadata and, in deep mode, adjacent lyric files."""
    search_term = f"%{query}%"
    
    tracks = _songs_only(db.query(Track)).filter(
        (Track.title.ilike(search_term)) |
        (Track.artist.ilike(search_term)) |
        (Track.album.ilike(search_term))
    ).order_by(Track.added_at.desc()).limit(limit).all()
    
    albums = _songs_only(db.query(
        Track.album.label("name"),
        Track.artist,
        func.count(Track.id).label("track_count"),
    )).filter(
        (Track.album.ilike(search_term)) |
        (Track.artist.ilike(search_term))
    ).group_by(Track.album, Track.artist).order_by(Track.album).limit(limit).all()

    lyric_matches = []
    if deep:
        normalized_query = query.casefold()
        media_dirs = ["/media", "/mnt/usb", "/home/pi/Music"]
        for media_dir in media_dirs:
            if not os.path.isdir(media_dir):
                continue
            for root, _, filenames in os.walk(media_dir):
                for filename in filenames:
                    if not filename.casefold().endswith(".lrc"):
                        continue
                    lyric_path = Path(root) / filename
                    try:
                        lyric_text = lyric_path.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    if normalized_query not in lyric_text.casefold():
                        continue
                    audio_path = lyric_path.with_suffix("")
                    matched_track = db.query(Track).filter(
                        Track.file_path == str(audio_path)
                    ).first()
                    lyric_matches.append({
                        "track_id": matched_track.id if matched_track else None,
                        "title": matched_track.title if matched_track else audio_path.name,
                        "file": str(lyric_path),
                    })
                    if len(lyric_matches) >= limit:
                        break
                if len(lyric_matches) >= limit:
                    break
            if len(lyric_matches) >= limit:
                break

        lyric_track_ids = {
            match["track_id"] for match in lyric_matches if match["track_id"] is not None
        }
        if lyric_track_ids:
            deep_tracks = db.query(Track).filter(Track.id.in_(lyric_track_ids)).all()
            existing_ids = {track.id for track in tracks}
            tracks.extend(track for track in deep_tracks if track.id not in existing_ids)

    return {
        "query": query,
        "limit": limit,
        "deep": deep,
        "tracks": [
            {
                "id": t.id,
                "file_path": t.file_path,
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "duration": t.duration,
                "track_number": t.track_number,
                "play_count": t.play_count,
                "favorite": t.favorite,
            }
            for t in tracks
        ],
        "albums": [
            {
                "id": index + 1,
                "name": a.name,
                "artist": a.artist,
                "track_count": a.track_count,
            }
            for index, a in enumerate(albums)
        ],
        "lyric_matches": lyric_matches,
    }


@router.get("/music/stats")
async def get_music_stats(db: Session = Depends(get_session)):
    """Get music library statistics"""
    total_tracks = _songs_only(db.query(func.count(Track.id))).scalar()
    songs = _songs_only(db.query(Track))
    total_albums = songs.with_entities(func.count(func.distinct(Track.album))).scalar() or 0
    total_artists = songs.with_entities(func.count(func.distinct(Track.artist))).scalar() or 0
    total_duration = songs.with_entities(func.sum(Track.duration)).scalar() or 0
    
    return {
        "total_tracks": total_tracks,
        "total_albums": total_albums,
        "total_artists": total_artists,
        "total_duration": total_duration,
    }
