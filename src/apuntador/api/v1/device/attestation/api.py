"""
Device attestation router.

This module provides endpoints for verifying device attestation
before certificate enrollment.
"""

from fastapi import APIRouter, HTTPException

from apuntador.api.v1.device.attestation.request import (
    DesktopAttestationRequest,
    DeviceCheckAttestationRequest,
    SafetyNetAttestationRequest,
)
from apuntador.api.v1.device.attestation.response import (
    DesktopAttestationResponse,
    DeviceCheckAttestationResponse,
    SafetyNetAttestationResponse,
)
from apuntador.api.v1.device.attestation.services import AttestationService
from apuntador.core.logging import logger
from apuntador.di import DeviceAttestationServiceDep

router = APIRouter()


@router.post("/android", response_model=SafetyNetAttestationResponse)
async def verify_android_safetynet(
    request: SafetyNetAttestationRequest,
    domain_service: DeviceAttestationServiceDep,
) -> SafetyNetAttestationResponse:
    """
    Verify Android SafetyNet attestation.

    This endpoint validates a SafetyNet attestation JWS token from an Android device.
    The attestation proves the device's integrity (not rooted/tampered).

    **Flow**:
    1. Client calls SafetyNet Attestation API on device
    2. Client sends JWS token + nonce to this endpoint
    3. Backend verifies JWS signature and nonce
    4. Backend checks CTS profile match and basic integrity
    5. Returns verification result

    **Requirements**:
    - Device must pass CTS (Compatibility Test Suite) profile match
    - Device must pass basic integrity check
    - Nonce must match the challenge sent to the device
    """
    try:
        service = AttestationService(domain_service)
        response = await service.verify_safetynet(request)
        return response
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"SafetyNet verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during SafetyNet verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during attestation verification",
        )


@router.post("/ios", response_model=DeviceCheckAttestationResponse)
async def verify_ios_devicecheck(
    request: DeviceCheckAttestationRequest,
    domain_service: DeviceAttestationServiceDep,
) -> DeviceCheckAttestationResponse:
    """
    Verify iOS DeviceCheck attestation.

    This endpoint validates a DeviceCheck token from an iOS device.
    The attestation proves the device's integrity (not jailbroken).

    **Flow**:
    1. Client calls DeviceCheck API on device
    2. Client sends device token + challenge to this endpoint
    3. Backend generates JWT for Apple API authentication
    4. Backend calls Apple DeviceCheck API
    5. Returns verification result

    **Note**: DeviceCheck verification requires Apple Developer credentials.
    If not configured, this endpoint will return status "unsupported".
    """
    try:
        service = AttestationService(domain_service)
        response = await service.verify_devicecheck(request)
        return response
    except NotImplementedError as e:
        logger.warning(f"DeviceCheck not configured: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        logger.warning(f"DeviceCheck verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during DeviceCheck verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during attestation verification",
        )


@router.post("/desktop", response_model=DesktopAttestationResponse)
async def verify_desktop_fingerprint(
    request: DesktopAttestationRequest,
    domain_service: DeviceAttestationServiceDep,
) -> DesktopAttestationResponse:
    """
    Verify desktop device fingerprint.

    Desktop platforms (Windows/macOS/Linux) don't have hardware-backed attestation
    like mobile devices, so we use device fingerprinting and rate limiting instead.

    **Flow**:
    1. Client collects hardware info (CPU, MAC address, hostname, etc.)
    2. Client generates SHA-256 fingerprint of hardware info
    3. Client sends fingerprint + device_id to this endpoint
    4. Backend checks fingerprint consistency and rate limits
    5. Returns verification result

    **Note**: Desktop attestation is less secure than mobile attestation
    due to lack of hardware-backed attestation. Use short certificate
    validity periods (7 days) for desktop devices.
    """
    try:
        service = AttestationService(domain_service)
        response = await service.verify_desktop(request)
        return response
    except ValueError as e:
        logger.warning(f"Desktop verification validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during desktop verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during attestation verification",
        )


@router.post("/clear-cache", status_code=204)
async def clear_attestation_cache(
    domain_service: DeviceAttestationServiceDep,
) -> None:
    """
    Clear attestation cache (admin endpoint).

    This endpoint clears all cached attestation results, forcing
    re-verification on the next request. Useful for testing or
    when cache needs to be invalidated.

    **Note**: In production, this should be protected with admin authentication.
    """
    try:
        service = AttestationService(domain_service)
        service.clear_cache()
    except Exception as e:
        logger.exception(f"Error clearing attestation cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear attestation cache")
