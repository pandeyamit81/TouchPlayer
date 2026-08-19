"""Background Whisper transcription service."""
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger

from app.database.models import Track, TrackTranscript
from app.database.session import SessionLocal


class TranscriptionService:
    """Run one local Whisper job at a time so playback stays responsive."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")

    def _whisper_binary(self) -> str | None:
        configured = os.environ.get("TOUCHPLAYER_WHISPER_BIN", "whisper-cli")
        return configured if shutil.which(configured) else None

    def _model_path(self) -> Path:
        return Path(os.environ.get(
            "TOUCHPLAYER_WHISPER_MODEL",
            "/opt/touchplayer/models/ggml-tiny.en.bin",
        ))

    def submit(self, track_id: int) -> bool:
        db = SessionLocal()
        try:
            transcript = db.query(TrackTranscript).filter(TrackTranscript.track_id == track_id).first()
            if transcript and transcript.status in {"queued", "running"}:
                return False
            if transcript is None:
                transcript = TrackTranscript(track_id=track_id)
                db.add(transcript)
            transcript.status = "queued"
            transcript.error = None
            db.commit()
        finally:
            db.close()
        self._executor.submit(self._run, track_id)
        return True

    def _run(self, track_id: int) -> None:
        db = SessionLocal()
        temp_dir = None
        try:
            track = db.query(Track).filter(Track.id == track_id).first()
            transcript = db.query(TrackTranscript).filter(TrackTranscript.track_id == track_id).first()
            if not track or not transcript:
                return

            binary = self._whisper_binary()
            model = self._model_path()
            if not binary:
                raise RuntimeError("Whisper is not installed; install whisper.cpp and whisper-cli")
            if not model.is_file():
                raise RuntimeError(f"Whisper model not found: {model}")
            if not Path(track.file_path).is_file():
                raise RuntimeError(f"Audio file not found: {track.file_path}")

            transcript.status = "running"
            transcript.model = model.name
            db.commit()

            temp_dir = tempfile.mkdtemp(prefix="touchplayer-whisper-")
            wav_path = Path(temp_dir) / "audio.wav"
            subprocess.run([
                "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                "-i", track.file_path, "-ar", "16000", "-ac", "1", str(wav_path),
            ], check=True, timeout=600)
            output_base = Path(temp_dir) / "transcript"
            subprocess.run([
                binary, "-m", str(model), "-f", str(wav_path),
                "-nt", "-otxt", "-of", str(output_base),
            ], check=True, timeout=3600, capture_output=True, text=True)
            text_path = output_base.with_suffix(".txt")
            text = text_path.read_text(encoding="utf-8").strip()
            if not text:
                raise RuntimeError("Whisper returned an empty transcript")

            transcript.status = "complete"
            transcript.text = text
            transcript.error = None
            db.commit()
        except Exception as exc:
            logger.error(f"Transcription failed for track {track_id}: {exc}")
            transcript = db.query(TrackTranscript).filter(TrackTranscript.track_id == track_id).first()
            if transcript:
                transcript.status = "failed"
                transcript.error = str(exc)
                db.commit()
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            db.close()


transcription_service = TranscriptionService()
