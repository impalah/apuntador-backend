"""OAuth Business Logic Services."""

from typing import Any

from apuntador.config import Settings
from apuntador.core.logging import logger
from apuntador.di import get_oauth_service
from apuntador.utils.pkce import generate_code_challenge
from apuntador.utils.security import generate_state, sign_data, verify_signed_data


class OAuthService:
    """Service class for OAuth operations."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize OAuth service.

        Args:
            settings: Application settings
        """
        self.settings = settings

    async def create_authorization(
        self,
        provider: str,
        code_verifier: str,
        redirect_uri: str,
        client_state: str | None = None,
    ) -> tuple[str, str]:
        """
        Create OAuth authorization URL.

        Args:
            provider: OAuth provider (googledrive, dropbox)
            code_verifier: PKCE code verifier
            redirect_uri: OAuth redirect URI
            client_state: Optional client state for CSRF

        Returns:
            Tuple of (authorization_url, signed_state)

        Raises:
            Exception: If authorization URL generation fails
        """
        logger.info(f"Starting OAuth authorization flow for provider: {provider}")
        logger.debug(
            f"Request details: redirect_uri={redirect_uri}, code_verifier={code_verifier[:20]}..., state={client_state}"
        )

        service = get_oauth_service(provider, self.settings, redirect_uri=redirect_uri)

        logger.debug(f"Service created: {service.__class__.__name__}")
        logger.debug(
            f"Service config: client_id={service.client_id}, redirect_uri={service.redirect_uri}"
        )

        # Generate code challenge from code verifier
        code_challenge = generate_code_challenge(code_verifier)
        logger.debug(
            f"Generated code_challenge for {provider}: {code_challenge[:20]}..."
        )

        # Generate state if not provided
        state = client_state or generate_state()
        logger.debug(f"Using state: {state[:8]}... (truncated)")

        # Sign state with code_verifier to verify later
        signed_state = sign_data(
            {
                "state": state,
                "code_verifier": code_verifier,
                "provider": provider,
                "redirect_uri": redirect_uri,
            }
        )

        # Generate authorization URL
        auth_url = service.get_authorization_url(
            code_challenge=code_challenge,
            state=signed_state,
        )

        logger.info(f"✅ Authorization URL generated successfully for {provider}")
        logger.info(f"🔗 FULL AUTHORIZATION URL: {auth_url}")
        logger.debug(f"URL length: {len(auth_url)} characters")

        return auth_url, signed_state

    async def exchange_code_for_tokens(
        self,
        provider: str,
        code: str,
        code_verifier: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access tokens.

        Args:
            provider: OAuth provider
            code: Authorization code
            code_verifier: PKCE code verifier
            state: Optional signed state for validation

        Returns:
            Token data dictionary with access_token, refresh_token, expires_in, token_type

        Raises:
            ValueError: If state validation fails
            Exception: If token exchange fails
        """
        logger.info(
            f"Exchanging authorization code for token with provider: {provider}"
        )

        redirect_uri = None

        # Verify state if provided
        if state:
            logger.debug("Verifying state parameter")
            state_data = verify_signed_data(state)
            if not state_data:
                logger.warning("Invalid state parameter in token exchange")
                raise ValueError("Invalid state")

            # Verify code_verifier matches
            if state_data.get("code_verifier") != code_verifier:
                logger.warning("Code verifier mismatch in token exchange")
                raise ValueError("Code verifier mismatch")

            # Extract redirect_uri from state
            redirect_uri = state_data.get("redirect_uri")
            logger.debug(f"Using redirect_uri from state: {redirect_uri}")

        service = get_oauth_service(provider, self.settings, redirect_uri=redirect_uri)

        # Exchange code for tokens
        logger.debug(f"Calling provider {provider} to exchange code for token")
        token_data = await service.exchange_code_for_token(
            code=code,
            code_verifier=code_verifier,
        )

        logger.info(f"Successfully exchanged code for token with {provider}")

        return token_data

    async def refresh_access_token(
        self,
        provider: str,
        refresh_token: str,
    ) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            provider: OAuth provider
            refresh_token: Refresh token

        Returns:
            Token data dictionary with new access_token

        Raises:
            Exception: If token refresh fails
        """
        logger.info(f"Refreshing access token with provider: {provider}")

        service = get_oauth_service(provider, self.settings)

        token_data = await service.refresh_access_token(
            refresh_token=refresh_token,
        )

        logger.info(f"Successfully refreshed token with {provider}")

        return token_data

    async def revoke_token(
        self,
        provider: str,
        token: str,
    ) -> bool:
        """
        Revoke an access token.

        Args:
            provider: OAuth provider
            token: Token to revoke

        Returns:
            True if revocation was successful, False otherwise

        Raises:
            Exception: If token revocation fails
        """
        logger.info(f"Revoking token with provider: {provider}")

        service = get_oauth_service(provider, self.settings)

        success = await service.revoke_token(token=token)

        logger.info(
            f"Token revocation {'successful' if success else 'failed'} with {provider}"
        )

        return success
