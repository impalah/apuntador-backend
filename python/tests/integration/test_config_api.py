"""Tests for configuration API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from apuntador.application import create_app
from apuntador.config import get_settings


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authorization headers for config endpoints."""
    settings = get_settings()
    return {"Authorization": f"Bearer {settings.secret_key}"}


def test_get_config_providers_success(client, auth_headers):
    """Test successful retrieval of provider configuration."""
    response = client.get("/config/providers", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], dict)
    assert "version" in data
    assert "cache_ttl" in data


def test_get_config_providers_missing_auth(client):
    """Test config endpoint without authorization header."""
    response = client.get("/config/providers")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Missing Authorization header" in response.json()["detail"]


def test_get_config_providers_invalid_auth_format(client):
    """Test config endpoint with invalid auth format."""
    response = client.get(
        "/config/providers", headers={"Authorization": "InvalidFormat"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid Authorization header format" in response.json()["detail"]


def test_get_config_providers_wrong_token(client):
    """Test config endpoint with wrong API key."""
    response = client.get(
        "/config/providers", headers={"Authorization": "Bearer wrong-token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid API key" in response.json()["detail"]


def test_get_config_providers_contains_google_drive(client, auth_headers):
    """Test that Google Drive provider is in configuration."""
    response = client.get("/config/providers", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "googledrive" in data["providers"]
    assert data["providers"]["googledrive"]["enabled"] is True


def test_get_config_providers_contains_dropbox(client, auth_headers):
    """Test that Dropbox provider is in configuration."""
    response = client.get("/config/providers", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "dropbox" in data["providers"]
    assert data["providers"]["dropbox"]["enabled"] is True
