"""
Examples of how to use settings in different contexts.

This file demonstrates the two ways to access configuration:
1. Dependency injection (FastAPI routers/endpoints)
2. Direct import (services, utils, scripts)
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apuntador.config import Settings, get_settings, settings

# ============================================================================
# OPTION 1: Using Dependency Injection (Recommended in endpoints)
# ============================================================================

router_di = APIRouter(tags=["examples-dependency-injection"])


@router_di.get("/example/di/project-info")
async def get_project_info_di(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """
    Example: Use Depends(get_settings) in FastAPI endpoints.

    Advantages:
    - FastAPI automatically refreshes if env vars change
    - Easy to mock in tests
    - Standard FastAPI pattern
    """
    return {
        "project_name": settings.project_name,
        "version": settings.project_version,
        "debug": str(settings.debug),
    }


@router_di.get("/example/di/oauth-config")
async def get_oauth_config_di(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Example: Access OAuth configuration with dependency injection."""
    return {
        "google_configured": bool(settings.google_client_id),
        "dropbox_configured": bool(settings.dropbox_client_id),
        "onedrive_configured": bool(settings.onedrive_client_id),
    }


# ============================================================================
# OPTION 2: Direct Import (For code outside FastAPI)
# ============================================================================

router_direct = APIRouter(tags=["examples-direct-import"])


@router_direct.get("/example/direct/project-info")
async def get_project_info_direct() -> dict[str, str]:
    """
    Example: Use global 'settings' instance directly.

    Advantages:
    - Simpler, no need for Depends()
    - Useful in code that's not FastAPI (utils, services, scripts)

    Disadvantages:
    - Doesn't auto-refresh (cached)
    - Harder to mock in tests
    """
    return {
        "project_name": settings.project_name,
        "version": settings.project_version,
        "debug": str(settings.debug),
    }


@router_direct.get("/example/direct/cors-config")
async def get_cors_config_direct() -> dict[str, any]:
    """Example: Use helper methods from settings."""
    return {
        "allowed_origins": settings.get_allowed_origins(),
        "allowed_methods": settings.get_cors_allowed_methods(),
        "allowed_headers": settings.get_cors_allowed_headers(),
    }


# ============================================================================
# OPTION 3: Calling get_settings() in non-FastAPI code
# ============================================================================


def example_service_function() -> str:
    """
    Example: Use settings in a service function.

    This is the recommended way for code outside FastAPI endpoints.
    """
    # Option A: Use global instance (simpler)
    project_name = settings.project_name

    # Option B: Call get_settings() (equivalent, but more explicit)
    current_settings = get_settings()
    project_version = current_settings.project_version

    return f"{project_name} v{project_version}"


class ExampleService:
    """
    Example: Use settings in a service class.
    """

    def __init__(self):
        """Option 1: Initialize with global instance."""
        self.config = settings

    @classmethod
    def from_settings(cls, settings: Settings):
        """Option 2: Inject settings as parameter."""
        instance = cls()
        instance.config = settings
        return instance

    def get_oauth_providers(self) -> list[str]:
        """Example: Method that uses configuration."""
        providers = []

        if self.config.google_client_id:
            providers.append("googledrive")

        if self.config.dropbox_client_id:
            providers.append("dropbox")

        if self.config.onedrive_client_id:
            providers.append("onedrive")

        return providers


# ============================================================================
# OPTION 4: Refresh settings (in tests or development)
# ============================================================================


def example_refresh_settings():
    """
    Example: Clear cache to refresh settings.

    Useful in:
    - Tests that change environment variables
    - Development with hot reload
    - Scripts that modify the .env file
    """
    # Clear cache
    get_settings.cache_clear()

    # Get new instance with updated values
    fresh_settings = get_settings()

    return fresh_settings


# ============================================================================
# SUMMARY: When to use each option?
# ============================================================================

"""
1. Dependency Injection (Depends):
    In FastAPI endpoints/routers
    When you need easy testing
    For auto-refresh in development
    Not available outside FastAPI

2. Global instance (settings):
    In services, utils, scripts
    Code that's not FastAPI
    Simpler and more direct
    Cacheado (no auto-refresh)

3. Llamar get_settings():
    Equivalente a usar 'settings'
    Más explícito
    Puedes limpiar cache si necesitas

Recomendación por contexto:
- FastAPI routers  Depends(get_settings)
- Services/utils  import settings
- Scripts standalone  get_settings() o settings
- Tests  Depends() + mocking
"""
