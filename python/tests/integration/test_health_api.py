"""Tests for health check endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from apuntador import __version__
from apuntador.application import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert "message" in data


def test_public_health_check(client):
    """Test public health check endpoint."""
    response = client.get("/health/public")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert data["message"] == "Public endpoint (no mTLS)"
