"""
Configuration API endpoints.

Provides configuration information to clients about available
cloud providers and backend capabilities.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from loguru import logger

from apuntador.config import Settings, get_settings
from apuntador.models.config import CloudProviderConfig, ProviderInfo

router = APIRouter()


def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Verify API key for configuration endpoints.

    This provides basic authentication to prevent unauthorized access
    to configuration information.

    Args:
        x_api_key: API key from request header.
        settings: Application settings.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    # For now, we use the SECRET_KEY as API key
    # In production, you might want a separate CONFIG_API_KEY
    expected_key = settings.secret_key

    if not x_api_key:
        logger.warning("Configuration request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != expected_key:
        logger.warning("Configuration request with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@router.get(
    "/providers",
    response_model=CloudProviderConfig,
    summary="Get cloud provider configuration",
    description="""
    Returns the list of enabled cloud providers and their configuration.
    
    Requires authentication via X-API-Key header.
    
    Clients should cache this response for the duration specified in cache_ttl.
    """,
    responses={
        200: {
            "description": "Cloud provider configuration",
            "content": {
                "application/json": {
                    "example": {
                        "providers": {
                            "googledrive": {"enabled": True, "requires_mtls": True},
                            "dropbox": {"enabled": True, "requires_mtls": True},
                        },
                        "version": "1.0.0",
                        "cache_ttl": 3600,
                    }
                }
            },
        },
        401: {"description": "Missing or invalid API key"},
    },
)
async def get_providers(
    _: None = Depends(verify_api_key),  # Authentication
    settings: Settings = Depends(get_settings),
) -> CloudProviderConfig:
    """
    Get cloud provider configuration.

    Returns information about which cloud providers are enabled
    and their authentication requirements.

    Args:
        settings: Application settings (injected).

    Returns:
        CloudProviderConfig: Provider configuration with enabled status.
    """
    logger.info("Fetching cloud provider configuration")

    # Get list of enabled providers from configuration
    enabled_providers = settings.get_enabled_cloud_providers()

    logger.debug(f"Enabled providers: {enabled_providers}")

    # Build provider configuration
    # All providers currently require mTLS except when accessed from web
    # (Web clients skip mTLS and use OAuth + CORS)
    providers_config: dict[str, ProviderInfo] = {}

    # Define all known providers
    all_providers = ["googledrive", "dropbox", "onedrive"]

    for provider_id in all_providers:
        is_enabled = provider_id in enabled_providers
        providers_config[provider_id] = ProviderInfo(
            enabled=is_enabled,
            requires_mtls=True,  # mTLS is required for mobile/desktop
            # Web clients are handled differently (no mTLS, just CORS)
        )

    config = CloudProviderConfig(
        providers=providers_config,
        version=settings.project_version,
        cache_ttl=3600,  # 1 hour cache
    )

    logger.info(
        f"Returning configuration for {len(enabled_providers)} enabled providers"
    )

    return config
