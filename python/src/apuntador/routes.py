"""
Routes registration for the FastAPI application.

Centralizes all router registrations for clean application setup.
"""

from fastapi import FastAPI

from apuntador.api.v1 import CONFIG_PREFIX
from apuntador.api.v1.config.api import router as config_router
from apuntador.api.v1.device.attestation.router import router as attestation_router
from apuntador.api.v1.device.router import router as device_router
from apuntador.api.v1.health.router import router as health_router
from apuntador.api.v1.oauth.router import router as oauth_router


def register_routes(app: FastAPI) -> None:
    """
    Register all application routers.

    Args:
        app: FastAPI application instance
    """
    # Health check endpoints (no prefix, public)
    app.include_router(health_router)

    # OAuth endpoints (versioned API)
    app.include_router(oauth_router)

    # Device enrollment endpoints (versioned API)
    app.include_router(device_router)

    # Device attestation endpoints (versioned API)
    app.include_router(attestation_router)

    # Configuration endpoints (versioned API, requires API key)
    app.include_router(config_router, prefix=CONFIG_PREFIX, tags=["configuration"])
