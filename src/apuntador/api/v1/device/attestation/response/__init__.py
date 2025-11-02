"""Response models for device attestation endpoints."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AttestationStatus(str, Enum):
    """Attestation verification status."""

    VALID = "valid"
    INVALID = "invalid"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class SafetyNetAttestationResponse(BaseModel):
    """Response model for SafetyNet attestation verification."""

    status: AttestationStatus = Field(
        ..., description="Verification status (valid/invalid/failed)"
    )
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Verification timestamp",
    )
    cts_profile_match: bool | None = Field(
        None,
        description="Whether device passes CTS (Compatibility Test Suite) profile match",
    )
    basic_integrity: bool | None = Field(
        None, description="Whether device passes basic integrity check"
    )
    advice: str | None = Field(
        None,
        description="Additional advice if attestation failed (e.g., 'RESTORE_TO_FACTORY_ROM')",
    )
    error_message: str | None = Field(
        None, description="Error message if verification failed"
    )


class DeviceCheckAttestationResponse(BaseModel):
    """Response model for DeviceCheck attestation verification."""

    status: AttestationStatus = Field(
        ..., description="Verification status (valid/invalid/failed)"
    )
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Verification timestamp",
    )
    integrity_verified: bool | None = Field(
        None, description="Whether device integrity was verified"
    )
    error_message: str | None = Field(
        None, description="Error message if verification failed"
    )


class DesktopAttestationResponse(BaseModel):
    """Response model for desktop device attestation."""

    status: AttestationStatus = Field(
        ..., description="Verification status (valid/invalid/failed)"
    )
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Verification timestamp",
    )
    fingerprint_match: bool | None = Field(
        None, description="Whether fingerprint matches previous enrollment"
    )
    rate_limit_ok: bool | None = Field(
        None, description="Whether device is within rate limits"
    )
    error_message: str | None = Field(
        None, description="Error message if verification failed"
    )


class AttestationVerificationResponse(BaseModel):
    """Generic attestation verification response."""

    status: AttestationStatus = Field(..., description="Verification status")
    platform: str = Field(..., description="Platform type")
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Verification timestamp",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific verification details",
    )
    error_message: str | None = Field(
        None, description="Error message if verification failed"
    )


class AttestationCacheEntry(BaseModel):
    """Model for caching attestation results.

    Cache attestation results to avoid repeated verification
    of the same device within a short time window (e.g., 1 hour).
    """

    device_id: str = Field(..., description="Device identifier")
    platform: str = Field(..., description="Platform type")
    status: AttestationStatus = Field(..., description="Verification status")
    timestamp: datetime = Field(..., description="Verification timestamp")
    expires_at: datetime = Field(
        ..., description="Cache expiration timestamp (e.g., 1 hour from now)"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Platform-specific details")

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        now = datetime.now(UTC)
        # Handle both naive and aware datetimes
        if self.expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now > self.expires_at


__all__ = [
    "AttestationStatus",
    "SafetyNetAttestationResponse",
    "DeviceCheckAttestationResponse",
    "DesktopAttestationResponse",
    "AttestationVerificationResponse",
    "AttestationCacheEntry",
]
