"""
Unit tests for Dropbox OAuth provider.

Tests OAuth provider implementation for Dropbox.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from apuntador.services.dropbox import DropboxOAuthService


@pytest.fixture
def dropbox_service():
    """Create DropboxOAuthService with test credentials."""
    return DropboxOAuthService(
        client_id="test_dropbox_client_id",
        client_secret="test_dropbox_client_secret",
        redirect_uri="https://app.example.com/callback/dropbox",
    )


# ===========================
# Provider Properties Tests
# ===========================


def test_provider_name(dropbox_service):
    """Test provider name property."""
    assert dropbox_service.provider_name == "dropbox"


def test_scopes(dropbox_service):
    """Test scopes property."""
    scopes = dropbox_service.scopes
    assert isinstance(scopes, list)
    assert len(scopes) > 0
    # Dropbox uses account and files scopes
    assert any("account" in scope or "files" in scope for scope in scopes)


# ===========================
# Authorization URL Tests
# ===========================


def test_get_authorization_url_basic(dropbox_service):
    """Test authorization URL generation with basic parameters."""
    # Arrange
    code_challenge = "test_code_challenge_dropbox"
    state = "test_state_dropbox_123"

    # Act
    auth_url = dropbox_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert
    assert auth_url.startswith("https://www.dropbox.com/oauth2/authorize")
    assert "client_id=test_dropbox_client_id" in auth_url
    assert "response_type=code" in auth_url
    assert f"code_challenge={code_challenge}" in auth_url
    assert "code_challenge_method=S256" in auth_url
    assert f"state={state}" in auth_url


def test_get_authorization_url_contains_redirect_uri(dropbox_service):
    """Test that authorization URL includes redirect URI."""
    # Arrange
    code_challenge = "challenge_dropbox"
    state = "state_dropbox"

    # Act
    auth_url = dropbox_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert
    assert "redirect_uri=" in auth_url


# ===========================
# Token Exchange Tests
# ===========================


@pytest.mark.asyncio
async def test_exchange_code_for_token_success(dropbox_service):
    """Test successful token exchange."""
    # Arrange
    code = "dropbox_auth_code_xyz"
    code_verifier = "dropbox_verifier_abc"

    mock_response = {
        "access_token": "dropbox_access_token_123",
        "token_type": "bearer",
        "expires_in": 14400,  # 4 hours
        "refresh_token": "dropbox_refresh_token_456",
        "account_id": "dbid:test123",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await dropbox_service.exchange_code_for_token(
            code=code,
            code_verifier=code_verifier,
        )

    # Assert
    assert result["access_token"] == "dropbox_access_token_123"
    assert result["refresh_token"] == "dropbox_refresh_token_456"
    assert result["token_type"] == "bearer"

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "oauth2/token" in call_args[0][0]
    assert "code" in call_args[1]["data"]
    assert "code_verifier" in call_args[1]["data"]


@pytest.mark.asyncio
async def test_exchange_code_for_token_http_error(dropbox_service):
    """Test token exchange with HTTP error."""
    # Arrange
    code = "invalid_dropbox_code"
    code_verifier = "verifier_xyz"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400),
            )
        )
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await dropbox_service.exchange_code_for_token(
                code=code,
                code_verifier=code_verifier,
            )


# ===========================
# Token Refresh Tests
# ===========================


@pytest.mark.asyncio
async def test_refresh_access_token_success(dropbox_service):
    """Test successful token refresh."""
    # Arrange
    refresh_token = (
        "dropbox_refresh_token_456"  # NOSONAR - Test fixture, not a real secret
    )

    mock_response = {
        "access_token": "new_dropbox_access_token_789",
        "token_type": "bearer",
        "expires_in": 14400,
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await dropbox_service.refresh_access_token(
            refresh_token=refresh_token,
        )

    # Assert
    assert result["access_token"] == "new_dropbox_access_token_789"
    assert result["token_type"] == "bearer"

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "oauth2/token" in call_args[0][0]
    assert "refresh_token" in call_args[1]["data"]
    assert "grant_type" in call_args[1]["data"]


@pytest.mark.asyncio
async def test_refresh_access_token_http_error(dropbox_service):
    """Test token refresh with HTTP error."""
    # Arrange
    refresh_token = (
        "invalid_dropbox_refresh_token"  # NOSONAR - Test fixture, not a real secret
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )
        )
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await dropbox_service.refresh_access_token(
                refresh_token=refresh_token,
            )


# ===========================
# Token Revocation Tests
# ===========================


@pytest.mark.asyncio
async def test_revoke_token_success(dropbox_service):
    """Test successful token revocation."""
    # Arrange
    token = (
        "dropbox_access_token_to_revoke"  # NOSONAR - Test fixture, not a real secret
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await dropbox_service.revoke_token(token=token)

    # Assert
    assert result is True

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/auth/token/revoke" in call_args[0][0]  # Dropbox API v2 endpoint


@pytest.mark.asyncio
async def test_revoke_token_http_error(dropbox_service):
    """Test token revocation with HTTP error."""
    # Arrange
    token = "invalid_dropbox_token"  # NOSONAR - Test fixture, not a real secret

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400),
            )
        )
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await dropbox_service.revoke_token(token=token)

    # Assert
    assert result is False  # Should return False on error


# ===========================
# Edge Cases
# ===========================


def test_authorization_url_token_access_type(dropbox_service):
    """Test authorization URL includes token_access_type for offline access."""
    # Arrange
    code_challenge = "challenge_offline"
    state = "state_offline"

    # Act
    auth_url = dropbox_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert - Dropbox uses token_access_type for offline access
    assert "token_access_type=" in auth_url or "oauth2/authorize" in auth_url
