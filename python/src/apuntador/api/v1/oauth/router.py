"""OAuth API Routes - Route registration only."""

from fastapi import APIRouter

from apuntador.api.v1 import OAUTH_PREFIX
from apuntador.api.v1.oauth import api

router = APIRouter()
router.include_router(api.router, prefix=OAUTH_PREFIX, tags=["OAuth"])
