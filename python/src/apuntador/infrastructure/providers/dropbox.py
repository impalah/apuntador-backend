"""
OAuth service for Dropbox.

Implementation of OAuth 2.0 flow for Dropbox API access.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from apuntador.domain.services.oauth_base import OAuthServiceBase


class DropboxOAuthService(OAuthServiceBase):
    """
    OAuth 2.0 service for Dropbox API.

    Supports both standard OAuth with client_secret and PKCE-only flow
    (client_secret optional).
    """

    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
    REVOKE_URL = "https://api.dropboxapi.com/2/auth/token/revoke"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "dropbox"

    @property
    def scopes(self) -> list[str]:
        """
        Dropbox scopes for file access.

        Returns:
            List containing file read and write scopes
        """
        return ["files.content.read", "files.content.write"]

    def get_authorization_url(
        self,
        code_challenge: str,
        state: str,
    ) -> str:
        """
        Generates Dropbox authorization URL with PKCE.

        Args:
            code_challenge: SHA256 hash of code_verifier
            state: State parameter for CSRF protection

        Returns:
            Complete authorization URL for user redirect
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "token_access_type": "offline",  # Request refresh token
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

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

        Note:
            client_secret is optional when using PKCE. If not provided,
            only PKCE verification is used.
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            return response.status_code == 200
