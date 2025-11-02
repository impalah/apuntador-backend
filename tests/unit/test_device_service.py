"""
Unit tests for DeviceService.

Tests business logic layer for device enrollment, renewal, and revocation.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from apuntador.api.v1.device.request import (
    EnrollmentRequest,
    RenewalRequest,
    RevocationRequest,
)
from apuntador.api.v1.device.services import DeviceService

# Realistic CSR for validation (100+ characters)
VALID_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIIC2jCCAcICAQAwgZQxCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlh
MRYwFAYDVQQHDA1TYW4gRnJhbmNpc2NvMRkwFwYDVQQKDBBFeGFtcGxlIENvbXBh
bnkxEzARBgNVBAsMClRlY2hub2xvZ3kxKDAmBgNVBAMMH2FuZHJvaWQtZGV2aWNl
LTEyMy5leGFtcGxlLmNvbQ==
-----END CERTIFICATE REQUEST-----"""


@pytest.fixture
def mock_ca():
    """Mock CertificateAuthority."""
    ca = MagicMock()
    ca.sign_csr = AsyncMock()
    ca.get_ca_certificate_pem = AsyncMock(
        return_value="-----BEGIN CERTIFICATE-----\nCA_CERT\n-----END CERTIFICATE-----"
    )
    ca.revoke_certificate = AsyncMock()
    return ca


@pytest.fixture
def mock_factory():
    """Mock InfrastructureFactory."""
    factory = MagicMock()
    factory.get_certificate_repository = MagicMock()
    return factory


@pytest.fixture
def device_service(mock_ca):
    """Create DeviceService with mocked CA."""
    return DeviceService(mock_ca)


@pytest.fixture
def device_service_with_factory(mock_ca, mock_factory):
    """Create DeviceService with mocked CA and factory."""
    return DeviceService(mock_ca, mock_factory)


# ===========================
# Enrollment Tests
# ===========================


@pytest.mark.asyncio
async def test_enroll_device_android_success(device_service, mock_ca):
    """Test successful Android device enrollment."""
    # Arrange
    request = EnrollmentRequest(
        csr=VALID_CSR,
        device_id="android-device-123",
        platform="android",
    )

    mock_cert = MagicMock(
        certificate_pem="-----BEGIN CERTIFICATE-----\nCERT_DATA\n-----END CERTIFICATE-----",
        serial="1234567890abcdef",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    mock_ca.sign_csr.return_value = mock_cert

    # Act
    result = await device_service.enroll_device(request)

    # Assert
    assert result.certificate == mock_cert.certificate_pem
    assert result.serial == mock_cert.serial
    assert (
        result.ca_certificate
        == "-----BEGIN CERTIFICATE-----\nCA_CERT\n-----END CERTIFICATE-----"
    )
    mock_ca.sign_csr.assert_called_once_with(
        csr_pem=request.csr,
        device_id=request.device_id,
        platform=request.platform,
    )


@pytest.mark.asyncio
async def test_enroll_device_desktop_success(device_service, mock_ca):
    """Test successful desktop device enrollment."""
    # Arrange
    request = EnrollmentRequest(
        csr=VALID_CSR,
        device_id="desktop-device-456",
        platform="desktop",
    )

    mock_cert = MagicMock(
        certificate_pem="-----BEGIN CERTIFICATE-----\nDESKTOP_CERT\n-----END CERTIFICATE-----",
        serial="fedcba0987654321",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    mock_ca.sign_csr.return_value = mock_cert

    # Act
    result = await device_service.enroll_device(request)

    # Assert
    assert result.certificate == mock_cert.certificate_pem
    assert result.serial == mock_cert.serial
    assert result.issued_at == mock_cert.issued_at
    assert result.expires_at == mock_cert.expires_at


@pytest.mark.asyncio
async def test_enroll_device_invalid_csr(device_service, mock_ca):
    """Test enrollment with invalid CSR raises ValueError."""
    # Arrange - PEM format but with invalid content
    invalid_csr = """-----BEGIN CERTIFICATE REQUEST-----
INVALID_BASE64_CONTENT_HERE_THAT_WONT_PARSE_CORRECTLY_BUT_LOOKS_LIKE
_A_VALID_PEM_STRUCTURE_WITH_ENOUGH_LENGTH_TO_PASS_MIN_LENGTH_VALIDATION
-----END CERTIFICATE REQUEST-----"""

    request = EnrollmentRequest(
        csr=invalid_csr,
        device_id="device-123",
        platform="android",
    )

    mock_ca.sign_csr.side_effect = ValueError("Invalid CSR format")

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid CSR format"):
        await device_service.enroll_device(request)


# ===========================
# Renewal Tests
# ===========================


@pytest.mark.asyncio
async def test_renew_certificate_success(
    device_service_with_factory, mock_ca, mock_factory
):
    """Test successful certificate renewal."""
    # Arrange
    request = RenewalRequest(
        csr=VALID_CSR,
        device_id="android-device-123",
        old_serial="1234567890ABCDEF",  # Uppercase hex
    )

    # Mock old certificate
    old_cert = MagicMock(
        serial="1234567890ABCDEF",
        platform="android",
        device_id="android-device-123",
    )

    # Mock new certificate
    new_cert = MagicMock(
        certificate_pem="-----BEGIN CERTIFICATE-----\nNEW_CERT\n-----END CERTIFICATE-----",
        serial="abcdef1234567890",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=old_cert)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo
    mock_ca.sign_csr.return_value = new_cert
    mock_ca.revoke_certificate.return_value = True

    # Act
    result = await device_service_with_factory.renew_certificate(request)

    # Assert
    assert result.certificate == new_cert.certificate_pem
    assert result.serial == new_cert.serial
    mock_ca.sign_csr.assert_called_once_with(
        csr_pem=request.csr,
        device_id=request.device_id,
        platform=old_cert.platform,
    )
    mock_ca.revoke_certificate.assert_called_once_with(request.device_id)


@pytest.mark.asyncio
async def test_renew_certificate_not_found(device_service_with_factory, mock_factory):
    """Test renewal when old certificate doesn't exist."""
    # Arrange
    request = RenewalRequest(
        csr=VALID_CSR,
        device_id="nonexistent-device",
        old_serial="0000000000000000",  # Valid hex format
    )

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=None)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo

    # Act & Assert
    with pytest.raises(ValueError, match="No certificate found"):
        await device_service_with_factory.renew_certificate(request)


@pytest.mark.asyncio
async def test_renew_certificate_serial_mismatch(
    device_service_with_factory, mock_factory
):
    """Test renewal with mismatched serial number."""
    # Arrange
    request = RenewalRequest(
        csr=VALID_CSR,
        device_id="android-device-123",
        old_serial="ABCD1234567890EF",  # Valid hex format but wrong serial
    )

    old_cert = MagicMock(
        serial="FEDCBA0987654321",  # Different serial
        platform="android",
    )

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=old_cert)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo

    # Act & Assert
    with pytest.raises(ValueError, match="Old serial number does not match"):
        await device_service_with_factory.renew_certificate(request)


@pytest.mark.asyncio
async def test_renew_certificate_without_factory(device_service):
    """Test renewal without infrastructure factory raises ValueError."""
    # Arrange
    request = RenewalRequest(
        csr=VALID_CSR,
        device_id="device-123",
        old_serial="1234567890ABCDEF",  # Valid uppercase hex
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Infrastructure factory not available"):
        await device_service.renew_certificate(request)


# ===========================
# Revocation Tests
# ===========================


@pytest.mark.asyncio
async def test_revoke_certificate_success(device_service, mock_ca):
    """Test successful certificate revocation."""
    # Arrange
    request = RevocationRequest(
        device_id="android-device-123",
        reason="Device lost",
    )

    mock_ca.revoke_certificate.return_value = True

    # Act
    result = await device_service.revoke_certificate(request)

    # Assert
    assert result.success is True
    assert result.device_id == request.device_id
    assert "revoked" in result.message.lower()
    mock_ca.revoke_certificate.assert_called_once_with(request.device_id)


@pytest.mark.asyncio
async def test_revoke_certificate_not_found(device_service, mock_ca):
    """Test revocation when certificate doesn't exist."""
    # Arrange
    request = RevocationRequest(
        device_id="nonexistent-device",
        reason=None,
    )

    mock_ca.revoke_certificate.return_value = False

    # Act
    result = await device_service.revoke_certificate(request)

    # Assert
    assert result.success is False
    assert result.device_id == request.device_id
    assert "No certificate found" in result.message


# ===========================
# Status Tests
# ===========================


@pytest.mark.asyncio
async def test_get_certificate_status_success(
    device_service_with_factory, mock_factory
):
    """Test getting certificate status."""
    # Arrange
    device_id = "android-device-123"

    now = datetime.now(UTC).replace(tzinfo=None)
    mock_cert = MagicMock(
        device_id=device_id,
        serial="1234567890abcdef",
        platform="android",
        issued_at=now - timedelta(days=10),
        expires_at=now + timedelta(days=20),
        revoked=False,
    )

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=mock_cert)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo

    # Act
    result = await device_service_with_factory.get_certificate_status(device_id)

    # Assert
    assert result.device_id == device_id
    assert result.serial == mock_cert.serial
    assert result.platform == mock_cert.platform
    assert result.revoked is False
    # Allow for timing drift (19-20 days)
    assert 19 <= result.days_until_expiry <= 20


@pytest.mark.asyncio
async def test_get_certificate_status_not_found(
    device_service_with_factory, mock_factory
):
    """Test getting status for nonexistent certificate."""
    # Arrange
    device_id = "nonexistent-device"

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=None)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo

    # Act & Assert
    with pytest.raises(ValueError, match="No certificate found"):
        await device_service_with_factory.get_certificate_status(device_id)


@pytest.mark.asyncio
async def test_get_certificate_status_without_factory(device_service):
    """Test getting status without infrastructure factory raises ValueError."""
    # Act & Assert
    with pytest.raises(ValueError, match="Infrastructure factory not available"):
        await device_service.get_certificate_status("device-123")


@pytest.mark.asyncio
async def test_get_certificate_status_expired(
    device_service_with_factory, mock_factory
):
    """Test getting status for expired certificate shows negative days."""
    # Arrange
    device_id = "expired-device"

    now = datetime.now(UTC).replace(tzinfo=None)
    mock_cert = MagicMock(
        device_id=device_id,
        serial="expired-serial",
        platform="desktop",
        issued_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=3),
        revoked=False,
    )

    mock_cert_repo = MagicMock()
    mock_cert_repo.get_certificate = AsyncMock(return_value=mock_cert)
    mock_factory.get_certificate_repository.return_value = mock_cert_repo

    # Act
    result = await device_service_with_factory.get_certificate_status(device_id)

    # Assert
    # Allow for timing drift (-4 to -3 days)
    assert -4 <= result.days_until_expiry <= -3


# ===========================
# CA Certificate Tests
# ===========================


@pytest.mark.asyncio
async def test_get_ca_certificate(device_service, mock_ca):
    """Test getting CA certificate."""
    # Act
    result = await device_service.get_ca_certificate()

    # Assert
    assert "certificate" in result
    assert (
        result["certificate"]
        == "-----BEGIN CERTIFICATE-----\nCA_CERT\n-----END CERTIFICATE-----"
    )
    assert result["format"] == "PEM"
    assert "truststore" in result["usage"].lower()
    mock_ca.get_ca_certificate_pem.assert_called_once()
