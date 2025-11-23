"""
Unit tests for device attestation service.

Tests cover:
- SafetyNet attestation verification (Android)
- DeviceCheck attestation verification (iOS)
- Desktop fingerprint verification
- Cache management
"""

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from apuntador.api.v1.device.attestation.request import (
    AttestationPlatform,
    DesktopAttestationRequest,
    DeviceCheckAttestationRequest,
    SafetyNetAttestationRequest,
)
from apuntador.api.v1.device.attestation.response import AttestationStatus
from apuntador.services.device_attestation import DeviceAttestationService


@pytest.fixture
def attestation_service():
    """Create attestation service for testing."""
    return DeviceAttestationService(
        google_api_key="test-api-key",
        apple_team_id="test-team-id",
        apple_key_id="test-key-id",
        apple_private_key="test-private-key",
        cache_ttl_seconds=60,  # 1 minute for testing
    )


def create_safetynet_token(
    nonce: str, cts_match: bool = True, basic_integrity: bool = True, advice: str = None
):
    """Helper to create SafetyNet JWS token."""
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "nonce": nonce,
        "timestampMs": int(datetime.now(UTC).timestamp() * 1000),
        "apkPackageName": "com.apuntador.app",
        "ctsProfileMatch": cts_match,
        "basicIntegrity": basic_integrity,
    }
    if advice:
        payload["advice"] = advice

    # Create JWS token (header.payload.signature)
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    )
    # Pad signature to make token > 100 chars
    signature = "fake-signature" * 10
    signature_b64 = base64.urlsafe_b64encode(signature.encode()).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


# ===========================
# Android SafetyNet Tests
# ===========================


def test_safetynet_valid_attestation(attestation_service):
    """Test successful SafetyNet attestation verification."""
    nonce = "test-nonce-123456"  # 18 chars (min 16)
    token = create_safetynet_token(nonce)

    request = SafetyNetAttestationRequest(
        jws_token=token,
        device_id="android-device-123",
        nonce=nonce,
    )

    response = attestation_service.verify_safetynet(request)

    assert response.status == AttestationStatus.VALID
    assert response.device_id == "android-device-123"
    assert response.cts_profile_match is True
    assert response.basic_integrity is True
    assert response.error_message is None


def test_safetynet_invalid_jws_format(attestation_service):
    """Test SafetyNet verification with invalid JWS format."""
    # Create a token that's > 100 chars but invalid format
    invalid_token = "a" * 120  # NOSONAR - Test fixture, not a real secret
    nonce = "test-nonce-456789"

    request = SafetyNetAttestationRequest(
        jws_token=invalid_token,
        device_id="android-device-456",
        nonce=nonce,
    )

    response = attestation_service.verify_safetynet(request)

    assert response.status == AttestationStatus.FAILED
    assert response.device_id == "android-device-456"
    assert response.error_message is not None


def test_safetynet_nonce_mismatch(attestation_service):
    """Test SafetyNet verification with nonce mismatch."""
    correct_nonce = "test-nonce-correct"
    wrong_nonce = "test-nonce-wronggg"
    token = create_safetynet_token(correct_nonce)

    request = SafetyNetAttestationRequest(
        jws_token=token,
        device_id="android-device-789",
        nonce=wrong_nonce,  # Different from token payload
    )

    response = attestation_service.verify_safetynet(request)

    assert response.status == AttestationStatus.INVALID
    assert response.error_message == "Nonce mismatch"


def test_safetynet_failed_integrity(attestation_service):
    """Test SafetyNet verification with failed integrity checks."""
    nonce = "test-nonce-failed1"
    token = create_safetynet_token(
        nonce=nonce,
        cts_match=False,
        basic_integrity=False,
        advice="RESTORE_TO_FACTORY_ROM",
    )

    request = SafetyNetAttestationRequest(
        jws_token=token,
        device_id="android-rooted-device",
        nonce=nonce,
    )

    response = attestation_service.verify_safetynet(request)

    assert response.status == AttestationStatus.INVALID
    assert response.cts_profile_match is False
    assert response.basic_integrity is False
    assert response.advice == "RESTORE_TO_FACTORY_ROM"


def test_safetynet_cache_hit(attestation_service):
    """Test SafetyNet attestation cache hit."""
    nonce = "test-nonce-cache123"
    token = create_safetynet_token(nonce)

    request = SafetyNetAttestationRequest(
        jws_token=token,
        device_id="android-cached-device",
        nonce=nonce,
    )

    # First request - should verify and cache
    response1 = attestation_service.verify_safetynet(request)

    # Verify cache was populated
    cache_key = f"android-cached-device:{AttestationPlatform.ANDROID.value}"
    assert cache_key in attestation_service._cache

    # Second request - should use cache
    response2 = attestation_service.verify_safetynet(request)

    # Both should have same status
    assert response1.status == response2.status == AttestationStatus.VALID


# ===========================
# iOS DeviceCheck Tests
# ===========================


def test_devicecheck_unsupported(attestation_service):
    """Test DeviceCheck when Apple credentials not configured."""
    # Create service without Apple credentials
    service_no_creds = DeviceAttestationService()

    # Create valid-length token and challenge
    device_token = "a" * 120  # NOSONAR - Test fixture, not a real secret
    challenge = "test-challenge-16c"  # 18 chars

    request = DeviceCheckAttestationRequest(
        device_token=device_token,
        device_id="ios-device-123",
        challenge=challenge,
    )

    response = service_no_creds.verify_devicecheck(request)

    assert response.status == AttestationStatus.UNSUPPORTED
    assert response.error_message == "DeviceCheck not configured"


def test_devicecheck_not_implemented(attestation_service):
    """Test DeviceCheck verification (not fully implemented yet)."""
    device_token = "b" * 120  # NOSONAR - Test fixture, not a real secret
    challenge = "test-challenge-17c"

    request = DeviceCheckAttestationRequest(
        device_token=device_token,
        device_id="ios-device-456",
        challenge=challenge,
    )

    response = attestation_service.verify_devicecheck(request)

    # Should return unsupported until fully implemented
    assert response.status == AttestationStatus.UNSUPPORTED
    assert "not implemented" in response.error_message.lower()


# ===========================
# Desktop Fingerprint Tests
# ===========================


def test_desktop_valid_fingerprint(attestation_service):
    """Test successful desktop fingerprint verification."""
    request = DesktopAttestationRequest(
        device_id="desktop-device-123",
        fingerprint="a" * 64,  # Valid SHA-256 hex
        platform_details={
            "os": "macOS",
            "arch": "arm64",
            "hostname": "test-macbook",
        },
    )

    response = attestation_service.verify_desktop(request)

    assert response.status == AttestationStatus.VALID
    assert response.device_id == "desktop-device-123"
    assert response.fingerprint_match is True
    assert response.rate_limit_ok is True


def test_desktop_cache_hit(attestation_service):
    """Test desktop fingerprint cache hit."""
    request = DesktopAttestationRequest(
        device_id="desktop-cached-device",
        fingerprint="b" * 64,
        platform_details={"os": "Linux"},
    )

    # First request - should verify and cache
    response1 = attestation_service.verify_desktop(request)

    # Verify cache was populated
    cache_key = f"desktop-cached-device:{AttestationPlatform.DESKTOP.value}"
    assert cache_key in attestation_service._cache

    # Second request - should use cache
    response2 = attestation_service.verify_desktop(request)

    # Both should have same status
    assert response1.status == response2.status == AttestationStatus.VALID


# ===========================
# Cache Management Tests
# ===========================


def test_cache_clear(attestation_service):
    """Test clearing attestation cache."""
    # Add some cache entries manually
    from apuntador.api.v1.device.attestation.response import AttestationCacheEntry

    entry1 = AttestationCacheEntry(
        device_id="device1",
        platform=AttestationPlatform.ANDROID,
        status=AttestationStatus.VALID,
        timestamp=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        details={},
    )
    entry2 = AttestationCacheEntry(
        device_id="device2",
        platform=AttestationPlatform.IOS,
        status=AttestationStatus.VALID,
        timestamp=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        details={},
    )

    attestation_service._cache["device1:android"] = entry1
    attestation_service._cache["device2:ios"] = entry2

    assert len(attestation_service._cache) == 2

    # Clear cache
    attestation_service.clear_cache()

    assert len(attestation_service._cache) == 0


def test_cache_expiration(attestation_service):
    """Test cache entry expiration."""
    from apuntador.api.v1.device.attestation.response import AttestationCacheEntry

    # Create expired entry
    expired_entry = AttestationCacheEntry(
        device_id="expired-device",
        platform=AttestationPlatform.ANDROID,
        status=AttestationStatus.VALID,
        timestamp=datetime.now(UTC) - timedelta(seconds=10),
        expires_at=datetime.now(UTC) - timedelta(seconds=5),
        details={},
    )

    attestation_service._cache["expired-device:android"] = expired_entry

    # Try to get expired entry
    result = attestation_service._get_cached_attestation(
        "expired-device", AttestationPlatform.ANDROID
    )

    # Should return None (expired)
    assert result is None
    # Should be removed from cache
    assert "expired-device:android" not in attestation_service._cache


# ===========================
# Edge Cases
# ===========================


def test_concurrent_attestation_requests(attestation_service):
    """Test handling concurrent attestation requests for same device."""
    nonce = "test-nonce-concurrent123"
    token = create_safetynet_token(nonce)

    request = SafetyNetAttestationRequest(
        jws_token=token,
        device_id="concurrent-device",
        nonce=nonce,
    )

    # Make 5 sequential requests (methods are synchronous now)
    responses = [attestation_service.verify_safetynet(request) for _ in range(5)]

    # All should return same status
    assert all(r.status == AttestationStatus.VALID for r in responses)
    # All should have same device_id
    assert all(r.device_id == "concurrent-device" for r in responses)
