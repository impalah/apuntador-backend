"""Device Enrollment API Routes - Route registration only."""

from fastapi import APIRouter

from apuntador.api.v1 import DEVICE_PREFIX
from apuntador.api.v1.device import api

router = APIRouter()
router.include_router(api.router, prefix=DEVICE_PREFIX, tags=["device-enrollment"])
