"""
TouchPlayer Database Tests
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, Track, Album, Artist


@pytest.fixture
def engine():
    """Create in-memory database engine"""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def session(engine):
    """Create database session"""
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_track(session):
    """Test creating a track"""
    track = Track(
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        duration=180,
        file_path="/music/test_track.mp3",
        file_hash="abc123def456",
        track_number=1,
        year=2023,
    )
    session.add(track)
    session.commit()
    
    assert track.id is not None
    assert track.title == "Test Track"


def test_create_album(session):
    """Test creating an album"""
    album = Album(
        name="Test Album",
        artist="Test Artist",
        year=2023,
        cover_art="/artwork/test_album.jpg",
    )
    session.add(album)
    session.commit()
    
    assert album.id is not None
    assert album.name == "Test Album"


def test_create_artist(session):
    """Test creating an artist"""
    artist = Artist(
        name="Test Artist",
        bio="A test artist",
        image="/artwork/test_artist.jpg",
    )
    session.add(artist)
    session.commit()
    
    assert artist.id is not None
    assert artist.name == "Test Artist"


def test_track_relationships(session):
    """Test track relationships"""
    album = Album(
        name="Test Album",
        artist="Test Artist",
        year=2023,
    )
    session.add(album)
    session.commit()
    
    track = Track(
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        duration=180,
        file_path="/music/test_track.mp3",
        file_hash="abc123def456",
        track_number=1,
        year=2023,
        album_id=album.id,
    )
    session.add(track)
    session.commit()
    
    assert track.album_id == album.id
    assert track.album == album
