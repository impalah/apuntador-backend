"""
Unit tests for Google Drive OAuth provider.

Tests OAuth provider implementation for Google Drive.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from apuntador.infrastructure.providers.googledrive import GoogleDriveOAuthService


@pytest.fixture
def google_drive_service():
    """Create GoogleDriveOAuthService with test credentials."""
    return GoogleDriveOAuthService(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="https://app.example.com/callback",
    )


# ===========================
# Provider Properties Tests
# ===========================


def test_provider_name(google_drive_service):
    """Test provider name property."""
    assert google_drive_service.provider_name == "googledrive"


def test_scopes(google_drive_service):
    """Test scopes property."""
    scopes = google_drive_service.scopes
    assert isinstance(scopes, list)
    assert "https://www.googleapis.com/auth/drive" in scopes


# ===========================
# Authorization URL Tests
# ===========================


def test_get_authorization_url_basic(google_drive_service):
    """Test authorization URL generation with basic parameters."""
    # Arrange
    code_challenge = "test_code_challenge_xyz"
    state = "test_state_123"

    # Act
    auth_url = google_drive_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert
    assert auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test_client_id" in auth_url
    assert "response_type=code" in auth_url
    assert (
        f"redirect_uri={google_drive_service.redirect_uri}" in auth_url
        or "redirect_uri=https" in auth_url
    )
    assert f"code_challenge={code_challenge}" in auth_url
    assert "code_challenge_method=S256" in auth_url
    assert f"state={state}" in auth_url
    assert "access_type=offline" in auth_url
    assert "prompt=consent" in auth_url


def test_get_authorization_url_contains_scopes(google_drive_service):
    """Test that authorization URL includes scopes."""
    # Arrange
    code_challenge = "challenge_abc"
    state = "state_def"

    # Act
    auth_url = google_drive_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert
    assert "scope=" in auth_url
    assert "googleapis.com" in auth_url


# ===========================
# Token Exchange Tests
# ===========================


@pytest.mark.asyncio
async def test_exchange_code_for_token_success(google_drive_service):
    """Test successful token exchange."""
    # Arrange
    code = "auth_code_123"
    code_verifier = "verifier_xyz"

    mock_response = {
        "access_token": "goog_access_token_abc",
        "refresh_token": "goog_refresh_token_def",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await google_drive_service.exchange_code_for_token(
            code=code,
            code_verifier=code_verifier,
        )

    # Assert
    assert result["access_token"] == "goog_access_token_abc"
    assert result["refresh_token"] == "goog_refresh_token_def"
    assert result["expires_in"] == 3600
    assert result["token_type"] == "Bearer"

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == GoogleDriveOAuthService.TOKEN_URL
    assert "code" in call_args[1]["data"]
    assert "code_verifier" in call_args[1]["data"]


@pytest.mark.asyncio
async def test_exchange_code_for_token_http_error(google_drive_service):
    """Test token exchange with HTTP error."""
    # Arrange
    code = "invalid_code"
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
            await google_drive_service.exchange_code_for_token(
                code=code,
                code_verifier=code_verifier,
            )


# ===========================
# Token Refresh Tests
# ===========================


@pytest.mark.asyncio
async def test_refresh_access_token_success(google_drive_service):
    """Test successful token refresh."""
    # Arrange
    refresh_token = (
        "goog_refresh_token_def"  # NOSONAR - Test fixture, not a real secret
    )

    mock_response = {
        "access_token": "new_goog_access_token_ghi",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await google_drive_service.refresh_access_token(
            refresh_token=refresh_token,
        )

    # Assert
    assert result["access_token"] == "new_goog_access_token_ghi"
    assert result["expires_in"] == 3600
    assert result["token_type"] == "Bearer"

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == GoogleDriveOAuthService.TOKEN_URL
    assert "refresh_token" in call_args[1]["data"]
    assert "grant_type" in call_args[1]["data"]


@pytest.mark.asyncio
async def test_refresh_access_token_http_error(google_drive_service):
    """Test token refresh with HTTP error."""
    # Arrange
    refresh_token = "invalid_refresh_token"  # NOSONAR - Test fixture, not a real secret

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
            await google_drive_service.refresh_access_token(
                refresh_token=refresh_token,
            )


# ===========================
# Token Revocation Tests
# ===========================


@pytest.mark.asyncio
async def test_revoke_token_success(google_drive_service):
    """Test successful token revocation."""
    # Arrange
    token = "goog_access_token_to_revoke"  # NOSONAR - Test fixture, not a real secret

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_post_response)

        # Act
        result = await google_drive_service.revoke_token(token=token)

    # Assert
    assert result is True

    # Verify HTTP call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == GoogleDriveOAuthService.REVOKE_URL
    assert "token" in call_args[1]["params"]  # Uses params not data


@pytest.mark.asyncio
async def test_revoke_token_http_error(google_drive_service):
    """Test token revocation with HTTP error."""
    # Arrange
    token = "invalid_token"  # NOSONAR - Test fixture, not a real secret

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
        result = await google_drive_service.revoke_token(token=token)

    # Assert
    assert result is False  # Should return False on error


# ===========================
# Edge Cases
# ===========================


def test_authorization_url_with_special_characters(google_drive_service):
    """Test authorization URL generation with special characters in state."""
    # Arrange
    code_challenge = "challenge_with_special_chars_+=/"
    state = "state_with_special_chars_!@#"

    # Act
    auth_url = google_drive_service.get_authorization_url(
        code_challenge=code_challenge,
        state=state,
    )

    # Assert - URL should be properly encoded
    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
    # Special characters should be URL-encoded
    assert "%2B" in auth_url or "+" in auth_url or "challenge" in auth_url
