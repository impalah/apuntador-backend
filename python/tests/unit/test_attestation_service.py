"""
Unit tests for AttestationService.

Tests business logic layer between controllers and domain service.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apuntador.api.v1.device.attestation.request import (
    DesktopAttestationRequest,
    DeviceCheckAttestationRequest,
    SafetyNetAttestationRequest,
)
from apuntador.api.v1.device.attestation.response import AttestationStatus
from apuntador.api.v1.device.attestation.services import AttestationService


@pytest.fixture
def mock_domain_service():
    """Mock DeviceAttestationService."""
    return MagicMock()


@pytest.fixture
def attestation_service(mock_domain_service):
    """Create AttestationService with mocked domain service."""
    return AttestationService(mock_domain_service)


# ===========================
# SafetyNet Tests
# ===========================


@pytest.mark.asyncio
async def test_verify_safetynet_success(attestation_service, mock_domain_service):
    """Test successful SafetyNet verification."""
    # Arrange
    request = SafetyNetAttestationRequest(
        jws_token="a" * 100,  # Min 100 chars for Pydantic validation
        device_id="android-device-123",
        nonce="base64encodednonce",
    )

    mock_response = MagicMock(
        status=AttestationStatus.VALID,
        device_id="android-device-123",
        cts_profile_match=True,
        basic_integrity=True,
    )
    mock_domain_service.verify_safetynet = AsyncMock(return_value=mock_response)

    # Act
    result = await attestation_service.verify_safetynet(request)

    # Assert
    assert result == mock_response
    mock_domain_service.verify_safetynet.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_verify_safetynet_failed_status(attestation_service, mock_domain_service):
    """Test SafetyNet verification with FAILED status raises ValueError."""
    # Arrange
    request = SafetyNetAttestationRequest(
        jws_token="b" * 100,
        device_id="android-device-123",
        nonce="base64encodednonce",
    )

    mock_response = MagicMock(
        status=AttestationStatus.FAILED,
        error_message="JWS signature invalid",
    )
    mock_domain_service.verify_safetynet = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="SafetyNet verification failed"):
        await attestation_service.verify_safetynet(request)


@pytest.mark.asyncio
async def test_verify_safetynet_invalid_status(
    attestation_service, mock_domain_service
):
    """Test SafetyNet verification with INVALID status raises ValueError."""
    # Arrange
    request = SafetyNetAttestationRequest(
        jws_token="c" * 100,
        device_id="android-device-123",
        nonce="base64encodednonce",
    )

    mock_response = MagicMock(
        status=AttestationStatus.INVALID,
        advice="RESTORE_TO_FACTORY_ROM",
    )
    mock_domain_service.verify_safetynet = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Device failed integrity check"):
        await attestation_service.verify_safetynet(request)


@pytest.mark.asyncio
async def test_verify_safetynet_no_error_message(
    attestation_service, mock_domain_service
):
    """Test SafetyNet verification with FAILED but no error message."""
    # Arrange
    request = SafetyNetAttestationRequest(
        jws_token="d" * 100,
        device_id="android-device-123",
        nonce="base64encodednonce",
    )

    mock_response = MagicMock(
        status=AttestationStatus.FAILED,
        error_message=None,
    )
    mock_domain_service.verify_safetynet = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown error"):
        await attestation_service.verify_safetynet(request)


# ===========================
# DeviceCheck Tests
# ===========================


@pytest.mark.asyncio
async def test_verify_devicecheck_success(attestation_service, mock_domain_service):
    """Test successful DeviceCheck verification."""
    # Arrange
    request = DeviceCheckAttestationRequest(
        device_token="e" * 100,
        device_id="ios-device-456",
        challenge="random-challenge-string",
    )

    mock_response = MagicMock(
        status=AttestationStatus.VALID,
        device_id="ios-device-456",
        integrity_verified=True,
    )
    mock_domain_service.verify_devicecheck = AsyncMock(return_value=mock_response)

    # Act
    result = await attestation_service.verify_devicecheck(request)

    # Assert
    assert result == mock_response
    mock_domain_service.verify_devicecheck.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_verify_devicecheck_unsupported(attestation_service, mock_domain_service):
    """Test DeviceCheck verification when not configured."""
    # Arrange
    request = DeviceCheckAttestationRequest(
        device_token="f" * 100,
        device_id="ios-device-456",
        challenge="random-challenge-string",
    )

    mock_response = MagicMock(status=AttestationStatus.UNSUPPORTED)
    mock_domain_service.verify_devicecheck = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(
        NotImplementedError, match="DeviceCheck verification not configured"
    ):
        await attestation_service.verify_devicecheck(request)


@pytest.mark.asyncio
async def test_verify_devicecheck_failed(attestation_service, mock_domain_service):
    """Test DeviceCheck verification with FAILED status."""
    # Arrange
    request = DeviceCheckAttestationRequest(
        device_token="g" * 100,
        device_id="ios-device-456",
        challenge="random-challenge-string",
    )

    mock_response = MagicMock(
        status=AttestationStatus.FAILED,
        error_message="Apple API returned 500",
    )
    mock_domain_service.verify_devicecheck = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="DeviceCheck verification failed"):
        await attestation_service.verify_devicecheck(request)


@pytest.mark.asyncio
async def test_verify_devicecheck_invalid(attestation_service, mock_domain_service):
    """Test DeviceCheck verification with INVALID status."""
    # Arrange
    request = DeviceCheckAttestationRequest(
        device_token="h" * 100,
        device_id="ios-device-456",
        challenge="random-challenge-string",
    )

    mock_response = MagicMock(status=AttestationStatus.INVALID)
    mock_domain_service.verify_devicecheck = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Device failed integrity check"):
        await attestation_service.verify_devicecheck(request)


# ===========================
# Desktop Tests
# ===========================


@pytest.mark.asyncio
async def test_verify_desktop_success(attestation_service, mock_domain_service):
    """Test successful desktop fingerprint verification."""
    # Arrange
    request = DesktopAttestationRequest(
        device_id="desktop-device-789",
        fingerprint="a" * 64,  # SHA-256 hex
        platform_details={"os": "Windows", "arch": "x64"},
    )

    mock_response = MagicMock(
        status=AttestationStatus.VALID,
        device_id="desktop-device-789",
        fingerprint_match=True,
        rate_limit_ok=True,
    )
    mock_domain_service.verify_desktop = AsyncMock(return_value=mock_response)

    # Act
    result = await attestation_service.verify_desktop(request)

    # Assert
    assert result == mock_response
    mock_domain_service.verify_desktop.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_verify_desktop_failed(attestation_service, mock_domain_service):
    """Test desktop verification with FAILED status."""
    # Arrange
    request = DesktopAttestationRequest(
        device_id="desktop-device-789",
        fingerprint="b" * 64,
        platform_details={"os": "Linux", "arch": "arm64"},
    )

    mock_response = MagicMock(
        status=AttestationStatus.FAILED,
        error_message="Database connection failed",
    )
    mock_domain_service.verify_desktop = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Desktop verification failed"):
        await attestation_service.verify_desktop(request)


@pytest.mark.asyncio
async def test_verify_desktop_invalid(attestation_service, mock_domain_service):
    """Test desktop verification with INVALID status."""
    # Arrange
    request = DesktopAttestationRequest(
        device_id="desktop-device-789",
        fingerprint="c" * 64,
        platform_details={"os": "macOS", "arch": "arm64"},
    )

    mock_response = MagicMock(
        status=AttestationStatus.INVALID,
        error_message="Fingerprint mismatch",
        fingerprint_match=False,
    )
    mock_domain_service.verify_desktop = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Device verification failed"):
        await attestation_service.verify_desktop(request)


@pytest.mark.asyncio
async def test_verify_desktop_no_error_message(
    attestation_service, mock_domain_service
):
    """Test desktop verification with FAILED but no error message."""
    # Arrange
    request = DesktopAttestationRequest(
        device_id="desktop-device-789",
        fingerprint="d" * 64,
        platform_details={},
    )

    mock_response = MagicMock(
        status=AttestationStatus.FAILED,
        error_message=None,
    )
    mock_domain_service.verify_desktop = AsyncMock(return_value=mock_response)

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown error"):
        await attestation_service.verify_desktop(request)


# ===========================
# Cache Tests
# ===========================


def test_clear_cache(attestation_service, mock_domain_service):
    """Test cache clearing delegates to domain service."""
    # Act
    attestation_service.clear_cache()

    # Assert
    mock_domain_service.clear_cache.assert_called_once()
