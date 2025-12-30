"""
OAuth service for Google Drive.

Implementation of OAuth 2.0 flow for Google Drive API access.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from apuntador.domain.services.oauth_base import OAuthServiceBase


class GoogleDriveOAuthService(OAuthServiceBase):
    """
    OAuth 2.0 service for Google Drive API.

    Implements the complete OAuth flow including:
    - Authorization URL generation with PKCE
    - Token exchange
    - Token refresh
    - Token revocation
    """

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "googledrive"

    @property
    def scopes(self) -> list[str]:
        """
        Google Drive scopes.

        Returns:
            List containing drive scope for full Drive access
        """
        return ["https://www.googleapis.com/auth/drive"]

    def get_authorization_url(
        self,
        code_challenge: str,
        state: str,
    ) -> str:
        """
        Generates Google authorization URL with PKCE.

        Args:
            code_challenge: SHA256 hash of code_verifier
            state: State parameter for CSRF protection

        Returns:
            Complete authorization URL for user redirect
        """
        from apuntador.core.logging import logger

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        logger.debug("📋 Google OAuth Parameters:")
        logger.debug(f"  - client_id: {self.client_id}")
        logger.debug(f"  - redirect_uri: {self.redirect_uri}")
        logger.debug(f"  - scope: {params['scope']}")
        logger.debug(f"  - response_type: {params['response_type']}")
        logger.debug(f"  - code_challenge_method: {params['code_challenge_method']}")
        logger.debug(f"  - access_type: {params['access_type']}")
        logger.debug(f"  - prompt: {params['prompt']}")

        url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.debug(f"📍 Generated Google Auth URL: {url}")
        return url

    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """
        Exchanges authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: Original PKCE code verifier

        Returns:
            Dict with access_token, refresh_token, expires_in, token_type

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """
        Refreshes expired access token.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            Dict with new access_token and expires_in

        Raises:
            httpx.HTTPStatusError: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def revoke_token(
        self,
        token: str,
    ) -> bool:
        """
        Revokes an access or refresh token.

        Args:
            token: Token to revoke (access or refresh)

        Returns:
            True if revocation successful, False otherwise
        """
        params = {"token": token}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                params=params,
            )
            return response.status_code == 200
