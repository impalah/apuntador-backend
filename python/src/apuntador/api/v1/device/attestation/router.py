"""Device Attestation API Routes - Route registration only."""

from fastapi import APIRouter

from apuntador.api.v1 import DEVICE_ATTESTATION_PREFIX
from apuntador.api.v1.device.attestation import api

router = APIRouter()
router.include_router(
    api.router, prefix=DEVICE_ATTESTATION_PREFIX, tags=["device-attestation"]
)
