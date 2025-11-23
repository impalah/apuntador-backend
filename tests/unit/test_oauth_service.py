"""Tests for OAuth service layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apuntador.api.v1.oauth.services import OAuthService
from apuntador.config import get_settings


@pytest.fixture
def oauth_service():
    """Create OAuth service instance."""
    settings = get_settings()
    return OAuthService(settings)


def test_oauth_service_initialization(oauth_service):
    """Test OAuth service initialization."""
    assert oauth_service.settings is not None


@patch("apuntador.api.v1.oauth.services.get_oauth_service")
def test_create_authorization(mock_get_service, oauth_service):
    """Test creating authorization URL."""
    mock_service = MagicMock()
    mock_service.client_id = "test-client-id"
    mock_service.redirect_uri = "http://localhost:3000/callback"
    mock_service.get_authorization_url = MagicMock(
        return_value="https://accounts.google.com/auth?code_challenge=test"
    )
    mock_get_service.return_value = mock_service

    auth_url, signed_state = oauth_service.create_authorization(
        provider="googledrive",
        code_verifier="test_code_verifier" * 10,  # Make it longer
        redirect_uri="http://localhost:3000/callback",
        client_state="client_state_123",
    )

    assert auth_url.startswith("https://accounts.google.com/auth")
    assert signed_state is not None
    assert isinstance(signed_state, str)


@patch("apuntador.api.v1.oauth.services.get_oauth_service")
def test_create_authorization_without_client_state(mock_get_service, oauth_service):
    """Test creating authorization URL without client state."""
    mock_service = MagicMock()
    mock_service.client_id = "test-client-id"
    mock_service.redirect_uri = "http://localhost:3000/callback"
    mock_service.get_authorization_url = MagicMock(
        return_value="https://accounts.google.com/auth"
    )
    mock_get_service.return_value = mock_service

    auth_url, signed_state = oauth_service.create_authorization(
        provider="googledrive",
        code_verifier="a" * 128,
        redirect_uri="http://localhost:3000/callback",
    )

    assert auth_url is not None
    assert signed_state is not None
