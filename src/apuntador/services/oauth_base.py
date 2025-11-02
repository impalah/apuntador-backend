"""
Abstract base class for OAuth 2.0 services.
"""

from abc import ABC, abstractmethod
from typing import Any


class OAuthServiceBase(ABC):
    """Base class for OAuth 2.0 services."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """
        Initializes the OAuth service.

        Args:
            client_id: Provider's client ID
            client_secret: Provider's client secret
            redirect_uri: Redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_authorization_url(
        self,
        code_challenge: str,
        state: str,
    ) -> str:
        """
        Generates the OAuth authorization URL.

        Args:
            code_challenge: PKCE code challenge
            state: State for CSRF validation

        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """
        Exchanges authorization code for access token.

        Args:
            code: Authorization code
            code_verifier: PKCE code verifier

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.
        """
        pass

    @abstractmethod
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """
        Refreshes the access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new access_token and expires_in
        """
        pass

    @abstractmethod
    async def revoke_token(
        self,
        token: str,
    ) -> bool:
        """
        Revokes a token.

        Args:
            token: Token to revoke

        Returns:
            True if revocation was successful
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (googledrive, dropbox, etc.)."""
        pass

    @property
    @abstractmethod
    def scopes(self) -> list[str]:
        """Scopes OAuth requeridos."""
        pass
