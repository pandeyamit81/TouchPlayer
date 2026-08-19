"""
TouchPlayer Test Configuration
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_track():
    """Sample track data"""
    return {
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "duration": 180,
        "file_path": "/music/test_track.mp3",
        "file_hash": "abc123def456",
        "track_number": 1,
        "year": 2023,
    }


@pytest.fixture
def sample_album():
    """Sample album data"""
    return {
        "name": "Test Album",
        "artist": "Test Artist",
        "year": 2023,
        "cover_art": "/artwork/test_album.jpg",
    }


@pytest.fixture
def sample_playlist():
    """Sample playlist data"""
    return {
        "name": "Test Playlist",
        "description": "A test playlist",
    }
