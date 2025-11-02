"""
OAuth service for Dropbox.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from apuntador.services.oauth_base import OAuthServiceBase


class DropboxOAuthService(OAuthServiceBase):
    """
    OAuth 2.0 service for Dropbox API.

    Implements the OAuth 2.0 authorization code flow with PKCE
    for secure authentication without requiring client secrets.
    Supports token exchange, refresh, and revocation.
    """

    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
    REVOKE_URL = "https://api.dropboxapi.com/2/auth/token/revoke"

    @property
    def provider_name(self) -> str:
        """
        Get the provider identifier.

        Returns:
            str: Provider name "dropbox"
        """
        return "dropbox"

    @property
    def scopes(self) -> list[str]:
        """
        Get the required OAuth scopes for Dropbox API.

        Returns:
            list[str]: List of required scopes for file operations
        """
        return ["files.content.read", "files.content.write"]

    def get_authorization_url(
        self,
        code_challenge: str,
        state: str,
    ) -> str:
        """
        Generate Dropbox authorization URL with PKCE.

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
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "token_access_type": "offline",  # To get refresh token
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

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
                - refresh_token: Long-lived refresh token
                - expires_in: Token expiration in seconds
                - token_type: Usually "bearer"

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        # Only add client_secret if present (PKCE doesn't require it)
        if self.client_secret:
            data["client_secret"] = self.client_secret

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
                - token_type: Usually "bearer"

        Raises:
            httpx.HTTPStatusError: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        # Only add client_secret if present (PKCE doesn't require it)
        if self.client_secret:
            data["client_secret"] = self.client_secret

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
        Revoke Dropbox access or refresh token.

        Args:
            token: Access token or refresh token to revoke

        Returns:
            bool: True if revocation successful, False otherwise
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            return response.status_code == 200
