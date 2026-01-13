"""Device Enrollment Response Models."""

from datetime import datetime

# Optional was unused
from pydantic import BaseModel, Field


class EnrollmentResponse(BaseModel):
    """
    Response after successful enrollment.

    Attributes:
        certificate: PEM-encoded signed certificate
        serial: Certificate serial number (hex)
        issued_at: Certificate issue timestamp
        expires_at: Certificate expiration timestamp
        ca_certificate: CA certificate for truststore (optional)
    """

    certificate: str = Field(..., description="PEM-encoded signed certificate")
    serial: str = Field(..., description="Certificate serial number (hex)")
    issued_at: datetime = Field(..., description="Certificate issue timestamp (UTC)")
    expires_at: datetime = Field(
        ..., description="Certificate expiration timestamp (UTC)"
    )
    ca_certificate: str | None = Field(
        None, description="CA certificate for client truststore"
    )


class RevocationResponse(BaseModel):
    """
    Response after certificate revocation.

    Attributes:
        success: Whether revocation was successful
        device_id: Device identifier
        message: Human-readable message
    """

    success: bool = Field(..., description="Whether revocation succeeded")
    device_id: str = Field(..., description="Device identifier")
    message: str = Field(..., description="Human-readable message")


class CertificateStatusResponse(BaseModel):
    """
    Response for certificate status check.

    Attributes:
        device_id: Device identifier
        serial: Certificate serial number
        platform: Device platform
        issued_at: Issue timestamp
        expires_at: Expiration timestamp
        revoked: Whether certificate is revoked
        days_until_expiry: Days remaining until expiration
    """

    device_id: str
    serial: str
    platform: str
    issued_at: datetime
    expires_at: datetime
    revoked: bool
    days_until_expiry: int
