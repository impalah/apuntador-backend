"""
OAuth 2.0 endpoints for Google Drive and Dropbox.

Handles authorization, callback, token exchange, token refresh, and token revocation
for multiple OAuth providers.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from apuntador.api.v1.oauth.request import (
    OAuthAuthorizeRequest,
    OAuthRefreshRequest,
    OAuthRevokeRequest,
    OAuthTokenRequest,
)
from apuntador.api.v1.oauth.response import (
    OAuthAuthorizeResponse,
    OAuthRevokeResponse,
    OAuthTokenResponse,
)
from apuntador.api.v1.oauth.services import OAuthService
from apuntador.core.logging import logger
from apuntador.di import SettingsDep
from apuntador.models import ErrorResponse
from apuntador.utils.security import verify_signed_data

router = APIRouter()


@router.post(
    "/authorize/{provider}",
    response_model=OAuthAuthorizeResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def authorize(
    provider: str,
    request: OAuthAuthorizeRequest,
    settings: SettingsDep,
) -> OAuthAuthorizeResponse:
    """
    Starts the OAuth authorization flow.

    Generates the OAuth provider's authorization URL with PKCE.

    Args:
        provider: OAuth provider (googledrive, dropbox)
        request: Request data (code_verifier, redirect_uri, state)
        settings: Application configuration

    Returns:
        Authorization URL and signed state
    """
    try:
        service = OAuthService(settings)
        auth_url, signed_state = service.create_authorization(
            provider=provider,
            code_verifier=request.code_verifier,
            redirect_uri=request.redirect_uri,
            client_state=request.state,
        )

        return OAuthAuthorizeResponse(
            authorization_url=auth_url,
            state=signed_state,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in OAuth authorization for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    settings: SettingsDep,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
) -> RedirectResponse:
    """
    OAuth callback called by the provider.

    This endpoint receives the authorization code and redirects to the client
    with the necessary parameters to complete the flow.

    Args:
        provider: OAuth provider
        code: Authorization code
        state: Signed state
        settings: Configuration

    Returns:
        Redirect to client with code and state
    """
    logger.info(f"📥 OAuth callback received for provider: {provider}")
    logger.debug(f"Code: {code[:20]}...")
    logger.debug(f"State: {state[:50]}...")

    try:
        # Verify signed state
        state_data = verify_signed_data(state)

        if not state_data:
            logger.warning(f"Invalid state received in OAuth callback for {provider}")
            # Redirect with error if state is invalid (fallback to apuntador scheme)
            return RedirectResponse(
                url=f"apuntador://oauth-callback?error=invalid_state&provider={provider}"
            )

        if state_data.get("provider") != provider:
            logger.warning(
                f"Provider mismatch in OAuth callback. "
                f"Expected: {provider}, Got: {state_data.get('provider')}"
            )
            redirect_uri = state_data.get("redirect_uri", "apuntador://oauth-callback")
            return RedirectResponse(
                url=f"{redirect_uri}?error=provider_mismatch&provider={provider}"
            )

        # Extract redirect_uri from signed state
        redirect_uri = state_data.get("redirect_uri", "apuntador://oauth-callback")
        logger.info(f"✅ State verified, redirecting to: {redirect_uri}")

        # Construct deep link with code and state
        redirect_url = f"{redirect_uri}?code={code}&state={state}&provider={provider}"

        logger.info(f"🔗 Redirecting to app: {redirect_url}")

        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        logger.error(f"❌ Error processing OAuth callback: {e}")
        # On error, try to redirect with error
        error_url = f"apuntador://oauth-callback?error=callback_failed&error_description={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)


@router.post(
    "/token/{provider}",
    response_model=OAuthTokenResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def exchange_token(
    provider: str,
    request: OAuthTokenRequest,
    settings: SettingsDep,
) -> OAuthTokenResponse:
    """
    Exchanges authorization code for access token.

    Args:
        provider: OAuth provider
        request: Code and code_verifier
        settings: Configuration

    Returns:
        Access token and refresh token
    """
    try:
        service = OAuthService(settings)
        token_data = await service.exchange_code_for_tokens(
            provider=provider,
            code=request.code,
            code_verifier=request.code_verifier,
            state=request.state,
        )

        return OAuthTokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in", 3600),
            token_type=token_data.get("token_type", "Bearer"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in token exchange: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error exchanging code for token with {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/refresh/{provider}",
    response_model=OAuthTokenResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def refresh_token(
    provider: str,
    request: OAuthRefreshRequest,
    settings: SettingsDep,
) -> OAuthTokenResponse:
    """
    Refreshes access token using refresh token.

    Args:
        provider: OAuth provider
        request: Refresh token
        settings: Configuration

    Returns:
        New access token
    """
    try:
        service = OAuthService(settings)
        token_data = await service.refresh_access_token(
            provider=provider,
            refresh_token=request.refresh_token,
        )

        return OAuthTokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in", 3600),
            token_type=token_data.get("token_type", "Bearer"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error refreshing token with {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/revoke/{provider}",
    response_model=OAuthRevokeResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def revoke_token(
    provider: str,
    request: OAuthRevokeRequest,
    settings: SettingsDep,
) -> OAuthRevokeResponse:
    """
    Revokes an access token.

    Args:
        provider: OAuth provider
        request: Token to revoke
        settings: Configuration

    Returns:
        Revocation result
    """
    try:
        service = OAuthService(settings)
        success = await service.revoke_token(
            provider=provider,
            token=request.token,
        )

        return OAuthRevokeResponse(
            success=success,
            message=(
                "Token revoked successfully" if success else "Failed to revoke token"
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error revoking token with {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
