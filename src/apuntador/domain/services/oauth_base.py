"""
Abstract base class for OAuth 2.0 services.

This module defines the contract that all OAuth service implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any


class OAuthServiceBase(ABC):
    """
    Base class for OAuth 2.0 services.

    All OAuth provider implementations (Google Drive, Dropbox, etc.) must inherit
    from this class and implement all abstract methods.
    """

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
            redirect_uri: Redirect URI for OAuth callback
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
            code_challenge: PKCE code challenge (SHA256 hash of code_verifier)
            state: State parameter for CSRF validation

        Returns:
            Authorization URL to redirect the user to
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
            code: Authorization code received from OAuth callback
            code_verifier: PKCE code verifier (original random string)

        Returns:
            Dict with access_token, refresh_token, expires_in, token_type, etc.
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
            refresh_token: Refresh token from initial authorization

        Returns:
            Dict with new access_token, expires_in, and optionally new refresh_token
        """
        pass

    @abstractmethod
    async def revoke_token(
        self,
        token: str,
    ) -> bool:
        """
        Revokes a token (access or refresh token).

        Args:
            token: Token to revoke

        Returns:
            True if revocation was successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Provider name identifier.

        Returns:
            Provider name (googledrive, dropbox, onedrive, etc.)
        """
        pass

    @property
    @abstractmethod
    def scopes(self) -> list[str]:
        """
        OAuth scopes required by this provider.

        Returns:
            List of scope strings
        """
        pass
