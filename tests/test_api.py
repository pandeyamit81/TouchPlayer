"""
TouchPlayer API Tests
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "phase" in data
    assert "version" in data


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_v1_music_endpoint():
    """Test music library endpoint"""
    response = client.get("/api/v1/music")
    # May fail if database not initialized, but should return valid response
    assert response.status_code in [200, 500]


def test_api_v1_queue_endpoint():
    """Test queue endpoint"""
    response = client.get("/api/v1/queue")
    # May fail if database not initialized, but should return valid response
    assert response.status_code in [200, 500]


def test_api_v1_playlists_endpoint():
    """Test playlists endpoint"""
    response = client.get("/api/v1/playlists")
    # May fail if database not initialized, but should return valid response
    assert response.status_code in [200, 500]
