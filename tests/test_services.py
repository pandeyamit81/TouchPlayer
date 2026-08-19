"""
TouchPlayer Service Tests
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_mpd_client():
    """Mock MPD client"""
    with patch('app.services.mpd_service.MPDClient') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch('app.services.library.db_session') as mock:
        session = Mock()
        mock.return_value = session
        yield session


def test_mpd_service_initialization(mock_mpd_client):
    """Test MPD service initialization"""
    from app.services.mpd_service import MPDService
    
    service = MPDService()
    assert service is not None
    assert service.client == mock_mpd_client


def test_mpd_service_play(mock_mpd_client):
    """Test play command"""
    from app.services.mpd_service import MPDService
    
    service = MPDService()
    service.play()
    mock_mpd_client.play.assert_called_once()


def test_mpd_service_pause(mock_mpd_client):
    """Test pause command"""
    from app.services.mpd_service import MPDService
    
    service = MPDService()
    service.pause()
    mock_mpd_client.pause.assert_called_once()


def test_mpd_service_stop(mock_mpd_client):
    """Test stop command"""
    from app.services.mpd_service import MPDService
    
    service = MPDService()
    service.stop()
    mock_mpd_client.stop.assert_called_once()


def test_mpd_service_volume(mock_mpd_client):
    """Test volume control"""
    from app.services.mpd_service import MPDService
    
    service = MPDService()
    service.set_volume(50)
    mock_mpd_client.setvol.assert_called_once_with(50)


def test_library_scanner_initialization():
    """Test library scanner initialization"""
    from app.services.library import MediaScanner
    
    scanner = MediaScanner()
    assert scanner is not None


def test_queue_manager_initialization():
    """Test queue manager initialization"""
    from app.services.queue import QueueManager
    
    manager = QueueManager()
    assert manager is not None


def test_playlist_manager_initialization():
    """Test playlist manager initialization"""
    from app.services.playlists import PlaylistManager
    
    manager = PlaylistManager()
    assert manager is not None
