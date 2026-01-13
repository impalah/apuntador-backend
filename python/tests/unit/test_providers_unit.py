"""Unit tests for OAuth providers (Google Drive and Dropbox)."""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from apuntador.infrastructure.providers.dropbox import DropboxOAuthService
from apuntador.infrastructure.providers.googledrive import GoogleDriveOAuthService


class TestGoogleDriveProvider:
    """Tests for Google Drive OAuth provider."""

    @pytest.fixture
    def google_service(self):
        """Create a Google Drive OAuth service instance."""
        return GoogleDriveOAuthService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:3000/callback",
        )

    def test_provider_name(self, google_service):
        """Test provider name."""
        assert google_service.provider_name == "googledrive"

    def test_scopes(self, google_service):
        """Test scopes configuration."""
        assert google_service.scopes == ["https://www.googleapis.com/auth/drive"]

    def test_get_authorization_url(self, google_service):
        """Test authorization URL generation."""
        code_challenge = "test-challenge"
        state = "test-state"

        auth_url = google_service.get_authorization_url(code_challenge, state)

        # Parse URL
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        # Verify base URL
        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert parsed.path == "/o/oauth2/v2/auth"

        # Verify parameters
        assert params["client_id"][0] == "test-client-id"
        assert params["response_type"][0] == "code"
        assert params["redirect_uri"][0] == "http://localhost:3000/callback"
        assert params["scope"][0] == "https://www.googleapis.com/auth/drive"
        assert params["code_challenge"][0] == "test-challenge"
        assert params["code_challenge_method"][0] == "S256"
        assert params["state"][0] == "test-state"
        assert params["access_type"][0] == "offline"
        assert params["prompt"][0] == "consent"

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, google_service):
        """Test successful token exchange."""
        mock_response = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await google_service.exchange_code_for_token(
            code="test-code",
            code_verifier="test-verifier",
        )

        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"
        assert result["expires_in"] == 3600

    @respx.mock
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, google_service):
        """Test successful token refresh."""
        mock_response = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await google_service.refresh_access_token(
            refresh_token="test-refresh-token"
        )

        assert result["access_token"] == "new-access-token"
        assert result["expires_in"] == 3600

    @respx.mock
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, google_service):
        """Test successful token revocation."""
        respx.post("https://oauth2.googleapis.com/revoke").mock(
            return_value=httpx.Response(200, json={})
        )

        result = await google_service.revoke_token(token="test-token")

        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, google_service):
        """Test failed token revocation."""
        respx.post("https://oauth2.googleapis.com/revoke").mock(
            return_value=httpx.Response(400, json={"error": "invalid_token"})
        )

        result = await google_service.revoke_token(token="test-token")

        assert result is False


class TestDropboxProvider:
    """Tests for Dropbox OAuth provider."""

    @pytest.fixture
    def dropbox_service(self):
        """Create a Dropbox OAuth service instance."""
        return DropboxOAuthService(
            client_id="test-dropbox-key",
            client_secret="test-dropbox-secret",
            redirect_uri="http://localhost:3000/callback",
        )

    def test_provider_name(self, dropbox_service):
        """Test provider name."""
        assert dropbox_service.provider_name == "dropbox"

    def test_scopes(self, dropbox_service):
        """Test scopes configuration."""
        assert "files.content.read" in dropbox_service.scopes
        assert "files.content.write" in dropbox_service.scopes

    def test_get_authorization_url(self, dropbox_service):
        """Test authorization URL generation."""
        code_challenge = "test-challenge"
        state = "test-state"

        auth_url = dropbox_service.get_authorization_url(code_challenge, state)

        # Parse URL
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        # Verify base URL
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.dropbox.com"
        assert parsed.path == "/oauth2/authorize"

        # Verify parameters
        assert params["client_id"][0] == "test-dropbox-key"
        assert params["response_type"][0] == "code"
        assert params["redirect_uri"][0] == "http://localhost:3000/callback"
        assert params["code_challenge"][0] == "test-challenge"
        assert params["code_challenge_method"][0] == "S256"
        assert params["state"][0] == "test-state"
        assert params["token_access_type"][0] == "offline"

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, dropbox_service):
        """Test successful token exchange."""
        mock_response = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        respx.post("https://api.dropboxapi.com/oauth2/token").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await dropbox_service.exchange_code_for_token(
            code="test-code",
            code_verifier="test-verifier",
        )

        assert result["access_token"] == "test-access-token"
        assert result["refresh_token"] == "test-refresh-token"

    @respx.mock
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, dropbox_service):
        """Test successful token refresh."""
        mock_response = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        respx.post("https://api.dropboxapi.com/oauth2/token").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await dropbox_service.refresh_access_token(
            refresh_token="test-refresh-token"
        )

        assert result["access_token"] == "new-access-token"

    @respx.mock
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, dropbox_service):
        """Test successful token revocation."""
        respx.post("https://api.dropboxapi.com/2/auth/token/revoke").mock(
            return_value=httpx.Response(200, json={})
        )

        result = await dropbox_service.revoke_token(token="test-token")

        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, dropbox_service):
        """Test failed token revocation."""
        respx.post("https://api.dropboxapi.com/2/auth/token/revoke").mock(
            return_value=httpx.Response(400, json={})
        )

        result = await dropbox_service.revoke_token(token="test-token")

        assert result is False
