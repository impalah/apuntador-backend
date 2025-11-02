"""Health Check API Routes - Route registration only."""

from fastapi import APIRouter

from apuntador.api.v1.health import api

# Health endpoints don't need a prefix (they're at root level)
router = APIRouter()
router.include_router(api.router, tags=["Health"])
