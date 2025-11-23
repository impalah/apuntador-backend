"""Tests for OAuth base service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from apuntador.services.oauth_base import OAuthServiceBase


class MockOAuthService(OAuthServiceBase):
    """Mock implementation of OAuth service for testing."""

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def scopes(self) -> list[str]:
        return ["scope1", "scope2"]

    def get_authorization_url(
        self, code_challenge: str, state: str, redirect_uri: str | None = None
    ) -> str:
        return f"https://mock.com/auth?challenge={code_challenge}&state={state}"

    async def exchange_code_for_token(
        self, code: str, code_verifier: str, redirect_uri: str | None = None
    ) -> dict:
        return {"access_token": "mock_token", "expires_in": 3600}

    async def refresh_access_token(self, refresh_token: str) -> dict:
        return {"access_token": "new_mock_token", "expires_in": 3600}

    async def revoke_token(self, token: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_oauth_service_provider_name():
    """Test OAuth service provider name property."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    assert service.provider_name == "mock"


@pytest.mark.asyncio
async def test_oauth_service_scopes():
    """Test OAuth service scopes property."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    assert service.scopes == ["scope1", "scope2"]


@pytest.mark.asyncio
async def test_oauth_service_authorization_url():
    """Test OAuth service authorization URL generation."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    url = service.get_authorization_url(
        code_challenge="test_challenge", state="test_state"
    )

    assert "challenge=test_challenge" in url
    assert "state=test_state" in url


@pytest.mark.asyncio
async def test_oauth_service_exchange_code():
    """Test OAuth service code exchange."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    result = await service.exchange_code_for_token(
        code="test_code", code_verifier="test_verifier"
    )

    assert "access_token" in result
    assert result["access_token"] == "mock_token"


@pytest.mark.asyncio
async def test_oauth_service_refresh_token():
    """Test OAuth service token refresh."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    result = await service.refresh_access_token("old_token")

    assert "access_token" in result
    assert result["access_token"] == "new_mock_token"


@pytest.mark.asyncio
async def test_oauth_service_revoke_token():
    """Test OAuth service token revocation."""
    service = MockOAuthService(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost/callback",
    )

    result = await service.revoke_token("test_token")

    assert result is True
