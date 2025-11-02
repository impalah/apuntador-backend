"""
Device enrollment API endpoints.

Handles device certificate enrollment, renewal, and revocation.
Uses Certificate Authority service to sign CSRs and manage certificates.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger

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
from apuntador.api.v1.device.services import DeviceService
from apuntador.di import CertificateAuthorityDep, InfrastructureFactoryDep

router = APIRouter()


@router.post(
    "/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new device",
    description="""
    Enroll a device by submitting a Certificate Signing Request (CSR).

    The backend signs the CSR with the CA private key and returns a
    short-lived client certificate (7-30 days validity).

    **Flow**:
    1. Device generates key pair (in HSM if mobile)
    2. Device creates CSR with public key
    3. Device submits CSR to this endpoint
    4. Backend validates CSR and device attestation (optional)
    5. Backend signs CSR with CA
    6. Device receives signed certificate
    7. Device stores certificate paired with private key

    **Platforms**:
    - Android: 30-day certificates (Android Keystore)
    - iOS: 30-day certificates (Secure Enclave)
    - Desktop: 7-day certificates (encrypted file storage)
    - Web: 1-day certificates (session-based)
    """,
)
async def enroll_device(
    request: EnrollmentRequest,
    ca: CertificateAuthorityDep,
) -> EnrollmentResponse:
    """
    Enroll a device and issue certificate.

    Args:
        request: Enrollment request with CSR and device info
        ca: Certificate Authority service (injected)

    Returns:
        Signed certificate and metadata

    Raises:
        HTTPException: If enrollment fails (400/500)
    """
    try:
        service = DeviceService(ca)
        response = await service.enroll_device(request)
        return response
    except ValueError as e:
        logger.error(f"Enrollment validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid enrollment request: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Enrollment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate signing failed",
        )


@router.post(
    "/renew",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Renew an existing certificate",
    description="""
    Renew an existing device certificate before expiration.

    Clients should renew certificates when:
    - Android/iOS: 5 days before expiration (30-day certs)
    - Desktop: 2 days before expiration (7-day certs)

    The old certificate is automatically revoked upon successful renewal.
    """,
)
async def renew_certificate(
    request: RenewalRequest,
    ca: CertificateAuthorityDep,
    factory: InfrastructureFactoryDep,
) -> EnrollmentResponse:
    """
    Renew a device certificate.

    Args:
        request: Renewal request with new CSR
        ca: Certificate Authority service (injected)
        factory: Infrastructure factory (injected)

    Returns:
        New signed certificate

    Raises:
        HTTPException: If renewal fails (400/404/500)
    """
    try:
        service = DeviceService(ca, factory)
        response = await service.renew_certificate(request)
        return response
    except ValueError as e:
        # ValueError includes "not found" and "serial mismatch" cases
        logger.error(f"Renewal validation failed: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid renewal request: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Renewal failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate renewal failed",
        )


@router.post(
    "/revoke",
    response_model=RevocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a device certificate",
    description="""
    Revoke a device certificate immediately.

    Use cases:
    - Device lost or stolen
    - Security compromise suspected
    - Device decommissioned
    - User logged out

    Revoked certificates are rejected by mTLS validation middleware.
    """,
)
async def revoke_certificate_endpoint(
    request: RevocationRequest,
    ca: CertificateAuthorityDep,
) -> RevocationResponse:
    """
    Revoke a device certificate.

    Args:
        request: Revocation request
        ca: Certificate Authority service (injected)

    Returns:
        Revocation status
    """
    try:
        service = DeviceService(ca)
        response = await service.revoke_certificate(request)
        return response
    except Exception as e:
        logger.exception(f"Revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate revocation failed",
        )


@router.get(
    "/status/{device_id}",
    response_model=CertificateStatusResponse,
    summary="Get certificate status",
    description="""
    Check the status of a device certificate.

    Returns certificate metadata including:
    - Serial number
    - Issue and expiration timestamps
    - Revocation status
    - Days until expiration

    Useful for monitoring and triggering automatic renewal.
    """,
)
async def get_certificate_status(
    device_id: str,
    factory: InfrastructureFactoryDep,
) -> CertificateStatusResponse:
    """
    Get certificate status for a device.

    Args:
        device_id: Device identifier
        factory: Infrastructure factory (injected)

    Returns:
        Certificate status information

    Raises:
        HTTPException: If certificate not found (404)
    """
    try:
        service = DeviceService(ca=None, factory=factory)  # type: ignore
        response = await service.get_certificate_status(device_id)
        return response
    except ValueError as e:
        logger.warning(f"Certificate not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status check failed",
        )


@router.get(
    "/ca-certificate",
    summary="Get CA certificate",
    description="""
    Download the CA certificate for client truststore.

    Clients should:
    1. Download this certificate during first enrollment
    2. Store in truststore (Android KeyStore, iOS Keychain, etc.)
    3. Use to verify server signatures during mTLS handshake

    Returns PEM-encoded X.509 certificate.
    """,
)
async def get_ca_certificate(
    ca: CertificateAuthorityDep,
) -> dict[str, Any]:
    """
    Get CA certificate for client truststore.

    Args:
        ca: Certificate Authority service (injected)

    Returns:
        CA certificate in PEM format
    """
    try:
        service = DeviceService(ca)
        response = await service.get_ca_certificate()
        return response
    except Exception as e:
        logger.exception(f"Failed to retrieve CA certificate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve CA certificate",
        )
