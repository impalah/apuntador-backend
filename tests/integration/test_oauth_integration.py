"""Integration tests for OAuth router endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apuntador.application import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def code_verifier():
    """Generate a valid code verifier."""
    return "VQm4dxVSU5CUn4FNrRDHCanXgZqqSs3tS_8Z0GuAN3TCMuWRtMnxvy6WoJURT3yNGq8YxtsKAbDFxOZE_CuQTodJDGzQw0mc66N6NAl-MKPgi8C3htx-nV4y3xush5KZ"


class TestOAuthAuthorize:
    """Tests for POST /api/oauth/authorize/{provider}"""

    def test_authorize_googledrive(self, client, code_verifier):
        """Test authorization for Google Drive."""
        response = client.post(
            "/api/oauth/authorize/googledrive",
            json={
                "code_verifier": code_verifier,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "authorization_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["authorization_url"]

    def test_authorize_dropbox(self, client, code_verifier):
        """Test authorization for Dropbox."""
        response = client.post(
            "/api/oauth/authorize/dropbox",
            json={
                "code_verifier": code_verifier,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "authorization_url" in data
        assert "state" in data
        assert "dropbox.com" in data["authorization_url"]

    def test_authorize_invalid_provider(self, client, code_verifier):
        """Test authorization with invalid provider."""
        response = client.post(
            "/api/oauth/authorize/invalid",
            json={
                "code_verifier": code_verifier,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )

        assert response.status_code == 500


class TestOAuthCallback:
    """Tests for GET /api/oauth/callback/{provider} and POST /api/oauth/token/{provider}"""

    def test_callback_redirect(self, client):
        """Test callback redirect for Google Drive."""
        from apuntador.utils.security import sign_data

        signed_state = sign_data(
            {
                "code_verifier": "test-verifier",
                "provider": "googledrive",
                "redirect_uri": "http://localhost:3000/callback",
            }
        )

        response = client.get(
            f"/api/oauth/callback/googledrive?code=test-code&state={signed_state}",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "code=test-code" in response.headers["location"]

    @patch("apuntador.api.v1.oauth.services.OAuthService.exchange_code_for_tokens")
    def test_token_exchange(self, mock_exchange, client):
        """Test token exchange endpoint."""
        mock_exchange.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        response = client.post(
            "/api/oauth/token/googledrive",
            json={
                "code": "test-code",
                "code_verifier": "test-verifier",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["access_token"] == "test-access-token"


class TestOAuthTokenRefresh:
    """Tests for POST /api/oauth/refresh/{provider}"""

    @patch("apuntador.api.v1.oauth.services.OAuthService.refresh_access_token")
    def test_refresh_token_googledrive(self, mock_refresh, client):
        """Test token refresh for Google Drive."""
        mock_refresh.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        response = client.post(
            "/api/oauth/refresh/googledrive",
            json={"refresh_token": "test-refresh-token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["access_token"] == "new-access-token"

    def test_refresh_token_missing_token(self, client):
        """Test token refresh without refresh token."""
        response = client.post(
            "/api/oauth/refresh/googledrive",
            json={},
        )

        assert response.status_code == 422


class TestOAuthTokenRevoke:
    """Tests for POST /api/oauth/revoke/{provider}"""

    @patch("apuntador.api.v1.oauth.services.OAuthService.revoke_token")
    def test_revoke_token_googledrive(self, mock_revoke, client):
        """Test token revocation for Google Drive."""
        mock_revoke.return_value = True

        response = client.post(
            "/api/oauth/revoke/googledrive",
            json={"token": "test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

    @patch("apuntador.api.v1.oauth.services.OAuthService.revoke_token")
    def test_revoke_token_failure(self, mock_revoke, client):
        """Test failed token revocation."""
        mock_revoke.return_value = False

        response = client.post(
            "/api/oauth/revoke/googledrive",
            json={"token": "test-token"},
        )

        # The endpoint returns 200 with success=False, not 500
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_revoke_token_missing_token(self, client):
        """Test token revocation without token."""
        response = client.post(
            "/api/oauth/revoke/googledrive",
            json={},
        )

        assert response.status_code == 422
