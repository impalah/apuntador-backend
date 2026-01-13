"""Tests for device request models validation."""

import pytest
from pydantic import ValidationError

from apuntador.api.v1.device.request import (
    EnrollmentRequest,
    RenewalRequest,
    RevocationRequest,
)

# Sample valid CSR for testing (meets min_length=100)
VALID_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFRlc3QxDTALBgNV
BAcMBFRlc3QxDTALBgNVBAoMBFRlc3QxDTALBgNVBAsMBFRlc3QxDTALBgNVBAMM
BFRlc3QxHTAbBgkqhkiG9w0BCQEWDnRlc3RAdGVzdC5jb20wggEiMA0GCSqGSIb3
-----END CERTIFICATE REQUEST-----"""


def test_enrollment_request_invalid_csr_too_short():
    """Test that CSR must meet minimum length."""
    with pytest.raises(ValidationError) as exc_info:
        EnrollmentRequest(
            csr="short",
            device_id="test-device-123",
            platform="android",
        )

    errors = exc_info.value.errors()
    assert any(error["type"] == "string_too_short" for error in errors)


def test_enrollment_request_invalid_csr_no_header():
    """Test that CSR must start with PEM header."""
    with pytest.raises(ValidationError) as exc_info:
        EnrollmentRequest(
            csr="NOT A VALID CSR" * 20,  # Long enough but invalid format
            device_id="test-device-123",
            platform="android",
        )

    errors = exc_info.value.errors()
    assert any("PEM format" in str(error) for error in errors)


def test_enrollment_request_invalid_csr_no_footer():
    """Test that CSR must end with PEM footer."""
    # CSR with header but missing footer (long enough to pass min_length)
    invalid_csr = "-----BEGIN CERTIFICATE REQUEST-----\n" + "A" * 100

    with pytest.raises(ValidationError) as exc_info:
        EnrollmentRequest(
            csr=invalid_csr,
            device_id="test-device-123",
            platform="android",
        )

    errors = exc_info.value.errors()
    assert any("PEM footer" in str(error) for error in errors)


def test_enrollment_request_invalid_platform():
    """Test that platform must match allowed values."""
    with pytest.raises(ValidationError) as exc_info:
        EnrollmentRequest(
            csr=VALID_CSR,
            device_id="test-device-123",
            platform="invalid_platform",
        )

    errors = exc_info.value.errors()
    assert any(error["type"] == "string_pattern_mismatch" for error in errors)


def test_enrollment_request_valid():
    """Test valid enrollment request."""
    request = EnrollmentRequest(
        csr=VALID_CSR,
        device_id="test-device-123",
        platform="android",
    )

    assert request.device_id == "test-device-123"
    assert request.platform == "android"


def test_renewal_request_valid():
    """Test valid renewal request."""
    request = RenewalRequest(
        csr=VALID_CSR,
        device_id="test-device-123",
        old_serial="ABCD1234",
    )

    assert request.device_id == "test-device-123"
    assert request.old_serial == "ABCD1234"


def test_renewal_request_invalid_csr_no_header():
    """Test that renewal CSR must start with PEM header."""
    with pytest.raises(ValidationError) as exc_info:
        RenewalRequest(
            csr="NOT A VALID CSR" * 20,
            device_id="test-device-123",
            old_serial="ABCD1234",
        )

    errors = exc_info.value.errors()
    assert any("PEM format" in str(error) for error in errors)


def test_renewal_request_invalid_serial_format():
    """Test that old_serial must match hex pattern."""
    with pytest.raises(ValidationError) as exc_info:
        RenewalRequest(
            csr=VALID_CSR,
            device_id="test-device-123",
            old_serial="invalid-serial-123",  # Lowercase and hyphens not allowed
        )

    errors = exc_info.value.errors()
    assert any(error["type"] == "string_pattern_mismatch" for error in errors)


def test_revocation_request_valid():
    """Test valid revocation request."""
    request = RevocationRequest(
        device_id="test-device-123",
        reason="Device lost or stolen",
    )

    assert request.device_id == "test-device-123"
    assert request.reason == "Device lost or stolen"
