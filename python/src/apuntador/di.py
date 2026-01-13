"""
Dependency injection container for apuntador backend.

This module provides centralized dependency injection using FastAPI's Depends
with typing.Annotated for clean type hints throughout the application.
"""

from typing import Annotated

from fastapi import Depends

from apuntador.config import Settings, get_settings
from apuntador.domain.services.oauth_base import OAuthServiceBase
from apuntador.infrastructure import InfrastructureFactory
from apuntador.infrastructure.providers.dropbox import DropboxOAuthService
from apuntador.infrastructure.providers.googledrive import GoogleDriveOAuthService
from apuntador.services.certificate_authority import CertificateAuthority
from apuntador.services.device_attestation import DeviceAttestationService

# ============================================================================
# Settings Dependencies
# ============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]
"""Injected Settings instance (cached via lru_cache)."""


# ============================================================================
# Infrastructure Dependencies
# ============================================================================


def get_infrastructure_factory(
    settings: SettingsDep,
) -> InfrastructureFactory:
    """
    Get infrastructure factory from settings.

    Args:
        settings: Application settings (injected)

    Returns:
        Configured infrastructure factory
    """
    return InfrastructureFactory.from_settings(settings)


InfrastructureFactoryDep = Annotated[
    InfrastructureFactory, Depends(get_infrastructure_factory)
]
"""Injected InfrastructureFactory instance."""


# ============================================================================
# Certificate Authority Dependencies
# ============================================================================


def get_certificate_authority(
    factory: InfrastructureFactoryDep,
) -> CertificateAuthority:
    """
    Get Certificate Authority service.

    Args:
        factory: Infrastructure factory (injected)

    Returns:
        Certificate Authority service
    """
    return CertificateAuthority(factory)


CertificateAuthorityDep = Annotated[
    CertificateAuthority, Depends(get_certificate_authority)
]
"""Injected CertificateAuthority service."""


# ============================================================================
# Device Attestation Dependencies
# ============================================================================


def get_device_attestation_service(
    settings: SettingsDep,
) -> DeviceAttestationService:
    """
    Get Device Attestation service.

    Args:
        settings: Application settings (injected)

    Returns:
        Device Attestation service
    """
    return DeviceAttestationService(
        google_api_key=(
            settings.google_api_key if hasattr(settings, "google_api_key") else None
        ),
        apple_team_id=(
            settings.apple_team_id if hasattr(settings, "apple_team_id") else None
        ),
        apple_key_id=(
            settings.apple_key_id if hasattr(settings, "apple_key_id") else None
        ),
        apple_private_key=(
            settings.apple_private_key
            if hasattr(settings, "apple_private_key")
            else None
        ),
        cache_ttl_seconds=getattr(settings, "attestation_cache_ttl", 3600),
    )


DeviceAttestationServiceDep = Annotated[
    DeviceAttestationService, Depends(get_device_attestation_service)
]
"""Injected DeviceAttestationService."""


# ============================================================================
# OAuth Service Dependencies
# ============================================================================


def get_google_drive_service(
    settings: SettingsDep,
) -> GoogleDriveOAuthService:
    """
    Get Google Drive OAuth service.

    Args:
        settings: Application settings (injected)

    Returns:
        Google Drive OAuth service

    Raises:
        ValueError: If credentials are not configured
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError("Google Drive OAuth credentials not configured")

    return GoogleDriveOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )


GoogleDriveServiceDep = Annotated[
    GoogleDriveOAuthService, Depends(get_google_drive_service)
]
"""Injected GoogleDriveOAuthService."""


def get_dropbox_service(
    settings: SettingsDep,
) -> DropboxOAuthService:
    """
    Get Dropbox OAuth service.

    Args:
        settings: Application settings (injected)

    Returns:
        Dropbox OAuth service

    Raises:
        ValueError: If credentials are not configured
    """
    if not settings.dropbox_client_id:
        raise ValueError("Dropbox OAuth credentials not configured")

    return DropboxOAuthService(
        client_id=settings.dropbox_client_id,
        client_secret=settings.dropbox_client_secret or "",
        redirect_uri=settings.dropbox_redirect_uri,
    )


DropboxServiceDep = Annotated[DropboxOAuthService, Depends(get_dropbox_service)]
"""Injected DropboxOAuthService."""


# ============================================================================
# OAuth Service Factory
# ============================================================================


def get_oauth_service(
    provider: str,
    settings: SettingsDep,
    redirect_uri: str | None = None,
) -> OAuthServiceBase:
    """
    Factory function to get the appropriate OAuth service by provider name.

    This is the main entry point for OAuth service dependency injection.
    Use this when you need dynamic provider selection based on request parameters.

    Args:
        provider: OAuth provider identifier (googledrive, dropbox)
        settings: Application settings (injected)
        redirect_uri: Optional redirect URI override (for Dropbox custom schemes)

    Returns:
        OAuth service instance for the specified provider

    Raises:
        ValueError: If the provider is not supported
        ValueError: If provider credentials are not configured

    Example:
        ```python
        @router.post("/oauth/authorize/{provider}")
        async def authorize(
            provider: str,
            settings: SettingsDep,
        ):
            service = get_oauth_service(provider, settings)
            # Use service...
        ```
    """
    if provider == "googledrive":
        if not settings.google_client_id or not settings.google_client_secret:
            raise ValueError("Google Drive OAuth credentials not configured")

        return GoogleDriveOAuthService(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri,
        )

    elif provider == "dropbox":
        if not settings.dropbox_client_id:
            raise ValueError("Dropbox OAuth credentials not configured")

        return DropboxOAuthService(
            client_id=settings.dropbox_client_id,
            client_secret=settings.dropbox_client_secret or "",
            redirect_uri=redirect_uri or settings.dropbox_redirect_uri,
        )

    else:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
