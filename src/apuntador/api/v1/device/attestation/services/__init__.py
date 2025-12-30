"""
Attestation service for device integrity verification.

This service provides business logic for verifying device attestation
across different platforms (Android SafetyNet, iOS DeviceCheck, Desktop).
"""

from apuntador.api.v1.device.attestation.request import (
    DesktopAttestationRequest,
    DeviceCheckAttestationRequest,
    SafetyNetAttestationRequest,
)
from apuntador.api.v1.device.attestation.response import (
    AttestationStatus,
    DesktopAttestationResponse,
    DeviceCheckAttestationResponse,
    SafetyNetAttestationResponse,
)
from apuntador.core.logging import logger
from apuntador.services.device_attestation import DeviceAttestationService


class AttestationService:
    """
    Service for device attestation verification.

    This service wraps the domain DeviceAttestationService and provides
    business logic for verifying device integrity across different platforms.
    """

    def __init__(self, domain_service: DeviceAttestationService):
        """
        Initialize attestation service.

        Args:
            domain_service: Domain service for device attestation verification
        """
        self.domain_service = domain_service

    async def verify_safetynet(
        self, request: SafetyNetAttestationRequest
    ) -> SafetyNetAttestationResponse:
        """
        Verify Android SafetyNet attestation.

        This method validates a SafetyNet attestation JWS token from an Android device.
        The attestation proves the device's integrity (not rooted/tampered).

        Args:
            request: SafetyNet attestation request with JWS token and nonce

        Returns:
            SafetyNet attestation response with verification result

        Raises:
            ValueError: If verification fails or device fails integrity check
        """
        logger.info(f"Verifying SafetyNet attestation for device: {request.device_id}")

        response = await self.domain_service.verify_safetynet(request)

        if response.status == AttestationStatus.FAILED:
            err_msg = response.error_message or "Unknown error"
            error_msg = f"SafetyNet verification failed: {err_msg}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if response.status == AttestationStatus.INVALID:
            error_msg = (
                f"Device failed integrity check: {response.advice or 'Unknown reason'}"
            )
            logger.warning(f"{error_msg} (device: {request.device_id})")
            raise ValueError(error_msg)

        logger.info(
            f"SafetyNet verification successful for device: "
            f"{request.device_id} (CTS={response.cts_profile_match}, "
            f"BasicIntegrity={response.basic_integrity})"
        )

        return response

    async def verify_devicecheck(
        self, request: DeviceCheckAttestationRequest
    ) -> DeviceCheckAttestationResponse:
        """
        Verify iOS DeviceCheck attestation.

        This method validates a DeviceCheck token from an iOS device.
        The attestation proves the device's integrity (not jailbroken).

        Args:
            request: DeviceCheck attestation request with device token and challenge

        Returns:
            DeviceCheck attestation response with verification result

        Raises:
            ValueError: If verification fails or device fails integrity check
            NotImplementedError: If DeviceCheck verification is not configured
        """
        logger.info(
            f"Verifying DeviceCheck attestation for device: {request.device_id}"
        )

        response = await self.domain_service.verify_devicecheck(request)

        if response.status == AttestationStatus.UNSUPPORTED:
            error_msg = "DeviceCheck verification not configured"
            logger.warning(error_msg)
            raise NotImplementedError(error_msg)

        if response.status == AttestationStatus.FAILED:
            err_msg = response.error_message or "Unknown error"
            error_msg = f"DeviceCheck verification failed: {err_msg}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if response.status == AttestationStatus.INVALID:
            error_msg = "Device failed integrity check"
            logger.warning(f"{error_msg} (device: {request.device_id})")
            raise ValueError(error_msg)

        logger.info(
            f"DeviceCheck verification successful for device: {request.device_id}"
        )

        return response

    async def verify_desktop(
        self, request: DesktopAttestationRequest
    ) -> DesktopAttestationResponse:
        """
        Verify desktop device fingerprint.

        Desktop platforms (Windows/macOS/Linux) don't have hardware-backed attestation
        like mobile devices, so we use device fingerprinting and rate limiting instead.

        Args:
            request: Desktop attestation request with fingerprint and platform details

        Returns:
            Desktop attestation response with verification result

        Raises:
            ValueError: If verification fails or device fails validation
        """
        logger.info(f"Verifying desktop fingerprint for device: {request.device_id}")

        response = await self.domain_service.verify_desktop(request)

        if response.status == AttestationStatus.FAILED:
            err_msg = response.error_message or "Unknown error"
            error_msg = f"Desktop verification failed: {err_msg}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if response.status == AttestationStatus.INVALID:
            err_msg = response.error_message or "Unknown reason"
            error_msg = f"Device verification failed: {err_msg}"
            logger.warning(f"{error_msg} (device: {request.device_id})")
            raise ValueError(error_msg)

        logger.info(f"Desktop verification successful for device: {request.device_id}")

        return response

    def clear_cache(self) -> None:
        """
        Clear attestation cache.

        This method clears all cached attestation results, forcing
        re-verification on the next request. Useful for testing or
        when cache needs to be invalidated.
        """
        logger.info("Clearing attestation cache")
        self.domain_service.clear_cache()


__all__ = ["AttestationService"]
