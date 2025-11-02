"""Device Enrollment Request Models."""

# Optional was unused

from pydantic import BaseModel, Field, field_validator


class EnrollmentRequest(BaseModel):
    """
    Request to enroll a device (submit CSR for signing).

    Attributes:
        csr: PEM-encoded Certificate Signing Request
        device_id: Unique device identifier
        platform: Device platform (android, ios, desktop, web)
        attestation: Optional device attestation token (SafetyNet, DeviceCheck)
    """

    csr: str = Field(
        ..., description="PEM-encoded Certificate Signing Request", min_length=100
    )
    device_id: str = Field(
        ...,
        description="Unique device identifier",
        min_length=5,
        max_length=128,
        pattern=r"^[a-zA-Z0-9\-_]+$",
    )
    platform: str = Field(
        ..., description="Device platform", pattern=r"^(android|ios|desktop|web)$"
    )
    attestation: str | None = Field(
        None, description="Device attestation token (SafetyNet, DeviceCheck)"
    )

    @field_validator("csr")
    @classmethod
    def validate_csr_format(cls, v: str) -> str:
        """Validate CSR is in PEM format."""
        if not v.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
            raise ValueError("CSR must be in PEM format")
        if not v.rstrip().endswith("-----END CERTIFICATE REQUEST-----"):
            raise ValueError("CSR must end with PEM footer")
        return v

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, v: str) -> str:
        """Normalize platform to lowercase."""
        return v.lower()


class RenewalRequest(BaseModel):
    """
    Request to renew an existing certificate.

    Attributes:
        csr: New PEM-encoded CSR
        device_id: Device identifier (must match existing certificate)
        old_serial: Serial number of certificate being renewed
    """

    csr: str = Field(..., description="New PEM-encoded CSR", min_length=100)
    device_id: str = Field(
        ..., description="Device identifier", min_length=5, max_length=128
    )
    old_serial: str = Field(
        ...,
        description="Serial number of certificate being renewed",
        pattern=r"^[A-F0-9]+$",
    )

    @field_validator("csr")
    @classmethod
    def validate_csr_format(cls, v: str) -> str:
        """Validate CSR is in PEM format."""
        if not v.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
            raise ValueError("CSR must be in PEM format")
        return v


class RevocationRequest(BaseModel):
    """
    Request to revoke a certificate.

    Attributes:
        device_id: Device identifier
        reason: Revocation reason (optional)
    """

    device_id: str = Field(
        ..., description="Device identifier", min_length=5, max_length=128
    )
    reason: str | None = Field(None, description="Revocation reason", max_length=256)
