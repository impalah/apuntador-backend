"""
Device service for certificate enrollment and management.

This service provides business logic for device certificate operations:
- Enrollment: Sign CSRs and issue new certificates
- Renewal: Issue new certificates and revoke old ones
- Revocation: Revoke compromised or decommissioned certificates
- Status: Check certificate validity and expiration
"""

from datetime import UTC, datetime
from typing import Any

from apuntador.api.v1.device.request import (
    EnrollmentRequest,
    RenewalRequest,
    RevocationRequest,
)
from apuntador.api.v1.device.response import (
    CertificateStatusResponse,
    EnrollmentResponse,
    RevocationResponse,
)
from apuntador.core.logging import logger
from apuntador.infrastructure.factory import InfrastructureFactory
from apuntador.services.certificate_authority import CertificateAuthority


class DeviceService:
    """
    Service for device certificate enrollment and management.

    This service wraps the Certificate Authority and provides business
    logic for device enrollment, renewal, revocation, and status checks.
    """

    def __init__(
        self,
        ca: CertificateAuthority,
        factory: InfrastructureFactory | None = None,
    ):
        """
        Initialize device service.

        Args:
            ca: Certificate Authority service for signing and revoking certificates
            factory: Infrastructure factory for repository access (optional for simple operations)
        """
        self.ca = ca
        self.factory = factory

    async def enroll_device(self, request: EnrollmentRequest) -> EnrollmentResponse:
        """
        Enroll a device and issue a certificate.

        This method signs a CSR and returns a client certificate with appropriate
        validity period based on platform (7-30 days).

        Args:
            request: Enrollment request with CSR and device info

        Returns:
            Signed certificate with metadata

        Raises:
            ValueError: If CSR validation fails or enrollment is invalid
        """
        logger.info(f"Enrolling device {request.device_id} ({request.platform})")

        # TODO: Validate device attestation (SafetyNet, DeviceCheck)
        # For now, we skip attestation validation

        # Sign CSR
        certificate = await self.ca.sign_csr(
            csr_pem=request.csr,
            device_id=request.device_id,
            platform=request.platform,
        )

        # Get CA certificate for client truststore
        ca_cert = await self.ca.get_ca_certificate_pem()

        logger.info(
            f"Device {request.device_id} enrolled successfully: "
            f"serial={certificate.serial}"
        )

        return EnrollmentResponse(
            certificate=certificate.certificate_pem,
            serial=certificate.serial,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            ca_certificate=ca_cert,
        )

    async def renew_certificate(self, request: RenewalRequest) -> EnrollmentResponse:
        """
        Renew a device certificate.

        This method issues a new certificate and automatically revokes the old one.
        Clients should renew before expiration (5 days for mobile, 2 days for desktop).

        Args:
            request: Renewal request with new CSR and old certificate info

        Returns:
            New signed certificate

        Raises:
            ValueError: If old certificate not found or serial mismatch
        """
        if not self.factory:
            raise ValueError("Infrastructure factory not available for renewal")

        logger.info(f"Renewing certificate for device {request.device_id}")

        cert_repo = self.factory.get_certificate_repository()

        # Verify old certificate exists
        old_cert = await cert_repo.get_certificate(request.device_id)
        if old_cert is None:
            error_msg = f"No certificate found for device {request.device_id}"
            logger.warning(error_msg)
            raise ValueError(error_msg)

        # Verify serial matches
        if old_cert.serial != request.old_serial:
            error_msg = "Old serial number does not match"
            logger.warning(
                f"{error_msg}: expected={old_cert.serial}, got={request.old_serial}"
            )
            raise ValueError(error_msg)

        # Sign new CSR (same platform as old certificate)
        new_certificate = await self.ca.sign_csr(
            csr_pem=request.csr,
            device_id=request.device_id,
            platform=old_cert.platform,
        )

        # Revoke old certificate
        await self.ca.revoke_certificate(request.device_id)

        # Get CA certificate
        ca_cert = await self.ca.get_ca_certificate_pem()

        logger.info(
            f"Certificate renewed for device {request.device_id}: "
            f"old_serial={old_cert.serial}, new_serial={new_certificate.serial}"
        )

        return EnrollmentResponse(
            certificate=new_certificate.certificate_pem,
            serial=new_certificate.serial,
            issued_at=new_certificate.issued_at,
            expires_at=new_certificate.expires_at,
            ca_certificate=ca_cert,
        )

    async def revoke_certificate(
        self, request: RevocationRequest
    ) -> RevocationResponse:
        """
        Revoke a device certificate.

        Use cases: device lost/stolen, security compromise, decommissioning.

        Args:
            request: Revocation request with device ID and reason

        Returns:
            Revocation status
        """
        logger.warning(
            f"Revoking certificate for device {request.device_id}: "
            f"reason={request.reason or 'not specified'}"
        )

        success = await self.ca.revoke_certificate(request.device_id)

        if success:
            return RevocationResponse(
                success=True,
                device_id=request.device_id,
                message=f"Certificate revoked for device {request.device_id}",
            )
        else:
            return RevocationResponse(
                success=False,
                device_id=request.device_id,
                message=f"No certificate found for device {request.device_id}",
            )

    async def get_certificate_status(self, device_id: str) -> CertificateStatusResponse:
        """
        Get certificate status for a device.

        Returns certificate metadata including expiration and revocation status.

        Args:
            device_id: Device identifier

        Returns:
            Certificate status information

        Raises:
            ValueError: If certificate not found
        """
        if not self.factory:
            raise ValueError("Infrastructure factory not available for status check")

        logger.info(f"Checking certificate status for device {device_id}")

        cert_repo = self.factory.get_certificate_repository()
        certificate = await cert_repo.get_certificate(device_id)

        if certificate is None:
            error_msg = f"No certificate found for device {device_id}"
            logger.warning(error_msg)
            raise ValueError(error_msg)

        # Calculate days until expiry
        now = datetime.now(UTC).replace(tzinfo=None)
        days_until_expiry = (certificate.expires_at - now).days

        return CertificateStatusResponse(
            device_id=certificate.device_id,
            serial=certificate.serial,
            platform=certificate.platform,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            revoked=certificate.revoked,
            days_until_expiry=days_until_expiry,
        )

    async def get_ca_certificate(self) -> dict[str, Any]:
        """
        Get CA certificate for client truststore.

        Clients should download this certificate during first enrollment
        and add it to their truststore for mTLS verification.

        Returns:
            CA certificate in PEM format with usage instructions
        """
        ca_cert_pem = await self.ca.get_ca_certificate_pem()

        return {
            "certificate": ca_cert_pem,
            "format": "PEM",
            "usage": "Add to client truststore for mTLS verification",
        }


__all__ = ["DeviceService"]
