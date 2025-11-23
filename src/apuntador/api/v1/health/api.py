"""
Health check endpoints.

Provides health check endpoints for monitoring service status.
"""

from fastapi import APIRouter

from apuntador import __version__
from apuntador.api.v1.health.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Service status and version
    """
    return HealthResponse(
        status="ok", version=__version__, message="Service is healthy"
    )


@router.get("/health/public", response_model=HealthResponse)
async def public_health_check() -> HealthResponse:
    """
    Public health check endpoint (no mTLS required).

    This endpoint is useful for testing HTTP connectivity without
    requiring client certificates. Use for development and testing only.

    Returns:
        Service status and version
    """
    return HealthResponse(
        status="ok", version=__version__, message="Public endpoint (no mTLS)"
    )
