"""
OAuth service for Google Drive.

This service can be used:
1. With dependency injection in FastAPI:
   service = GoogleDriveOAuthService(settings)

2. Directly importing settings:
   from apuntador.config import settings
   service = GoogleDriveOAuthService(
       client_id=settings.google_client_id,
       client_secret=settings.google_client_secret,
       redirect_uri=settings.google_redirect_uri,
   )
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from apuntador.core.logging import logger
from apuntador.services.oauth_base import OAuthServiceBase


class GoogleDriveOAuthService(OAuthServiceBase):
    """
    OAuth 2.0 service for Google Drive API.

    Implements Google's OAuth 2.0 authorization code flow with PKCE.
    Supports offline access for long-lived refresh tokens and full
    Drive API access.
    """

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    @property
    def provider_name(self) -> str:
        """
        Get the provider identifier.

        Returns:
            str: Provider name "googledrive"
        """
        return "googledrive"

    @property
    def scopes(self) -> list[str]:
        """
        Get the required OAuth scopes for Google Drive API.

        Returns:
            list[str]: List of required scopes for Drive access
        """
        return ["https://www.googleapis.com/auth/drive"]

    def get_authorization_url(
        self,
        code_challenge: str,
        state: str,
    ) -> str:
        """
        Generate Google authorization URL with PKCE.

        Uses offline access to obtain refresh tokens and forces
        consent screen to ensure refresh token is issued.

        Args:
            code_challenge: SHA256 hash of the code verifier (PKCE)
            state: State parameter for CSRF protection

        Returns:
            str: Complete authorization URL for user redirect
        """

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",  # To get refresh token
            "prompt": "consent",  # Force consent screen
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
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: Original PKCE code verifier (128-char random string)

        Returns:
            dict: Token response containing:
                - access_token: OAuth access token
                - refresh_token: Long-lived refresh token (if offline access granted)
                - expires_in: Token expiration in seconds
                - token_type: Usually "Bearer"
                - scope: Granted scopes

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
            result: dict[str, Any] = response.json()
            return result

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """
        Refresh expired access token using refresh token.

        Args:
            refresh_token: Long-lived refresh token from initial authorization

        Returns:
            dict: Token response containing:
                - access_token: New OAuth access token
                - expires_in: Token expiration in seconds
                - token_type: Usually "Bearer"

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
            result: dict[str, Any] = response.json()
            return result

    async def revoke_token(
        self,
        token: str,
    ) -> bool:
        """
        Revoke Google access or refresh token.

        Args:
            token: Access token or refresh token to revoke

        Returns:
            bool: True if revocation successful, False otherwise
        """
        params = {"token": token}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                params=params,
            )
            return response.status_code == 200
