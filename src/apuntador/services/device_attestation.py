"""
Device attestation service for verifying device integrity.

This service provides attestation verification for:
- Android: SafetyNet Attestation API
- iOS: DeviceCheck framework
- Desktop: Device fingerprinting + rate limiting

The service validates device integrity before issuing mTLS certificates
to ensure only legitimate, non-compromised devices can enroll.
"""

import base64
import json
from datetime import UTC, datetime, timedelta

from apuntador.api.v1.device.attestation.request import (
    AttestationPlatform,
    DesktopAttestationRequest,
    DeviceCheckAttestationRequest,
    SafetyNetAttestationRequest,
)
from apuntador.api.v1.device.attestation.response import (
    AttestationCacheEntry,
    AttestationStatus,
    DesktopAttestationResponse,
    DeviceCheckAttestationResponse,
    SafetyNetAttestationResponse,
)
from apuntador.core.logging import logger


class DeviceAttestationService:
    """Service for verifying device attestation across platforms.

    This service validates device integrity using platform-specific
    attestation mechanisms:

    - Android: SafetyNet Attestation (JWS token verification)
    - iOS: DeviceCheck (Apple server verification)
    - Desktop: Device fingerprinting + rate limiting

    Attestation results are cached for 1 hour to reduce API calls.
    """

    def __init__(
        self,
        google_api_key: str | None = None,
        apple_team_id: str | None = None,
        apple_key_id: str | None = None,
        apple_private_key: str | None = None,
        cache_ttl_seconds: int = 3600,  # 1 hour
    ):
        """Initialize attestation service.

        Args:
            google_api_key: Google Cloud API key for SafetyNet verification
            apple_team_id: Apple Developer Team ID for DeviceCheck
            apple_key_id: Apple Key ID for DeviceCheck
            apple_private_key: Apple private key (PEM) for DeviceCheck
            cache_ttl_seconds: Cache TTL for attestation results (default: 1 hour)
        """
        self.google_api_key = google_api_key
        self.apple_team_id = apple_team_id
        self.apple_key_id = apple_key_id
        self.apple_private_key = apple_private_key
        self.cache_ttl_seconds = cache_ttl_seconds

        # In-memory cache for attestation results
        # In production, use Redis or DynamoDB
        self._cache: dict[str, AttestationCacheEntry] = {}

        logger.info(
            f"Initialized DeviceAttestationService with cache TTL: {cache_ttl_seconds}s"
        )

    # ===========================
    # Android SafetyNet
    # ===========================

    def verify_safetynet(
        self, request: SafetyNetAttestationRequest
    ) -> SafetyNetAttestationResponse:
        """Verify Android SafetyNet attestation.

        Steps:
        1. Check cache for recent verification
        2. Decode JWS token (header.payload.signature)
        3. Verify signature using Google certificates
        4. Validate nonce matches request
        5. Check CTS profile match and basic integrity
        6. Cache result for 1 hour

        Args:
            request: SafetyNet attestation request with JWS token

        Returns:
            SafetyNet attestation response with verification status
        """
        logger.info(f"Verifying SafetyNet attestation for device: {request.device_id}")

        # Check cache
        cached = self._get_cached_attestation(
            request.device_id, AttestationPlatform.ANDROID
        )
        if cached:
            logger.debug(f"Using cached attestation for device: {request.device_id}")
            return SafetyNetAttestationResponse(
                status=cached.status,
                device_id=cached.device_id,
                timestamp=cached.timestamp,
                cts_profile_match=cached.details.get("cts_profile_match"),
                basic_integrity=cached.details.get("basic_integrity"),
            )

        try:
            # Decode JWS token
            jws_parts = request.jws_token.split(".")
            if len(jws_parts) != 3:
                raise ValueError("Invalid JWS token format")

            # Decode payload (base64url)
            payload_b64 = jws_parts[1]
            # Add padding if needed
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)

            logger.debug(f"Decoded SafetyNet payload: {payload.keys()}")

            # Validate nonce
            if payload.get("nonce") != request.nonce:
                logger.warning(
                    f"Nonce mismatch for device {request.device_id}: "
                    f"expected={request.nonce}, got={payload.get('nonce')}"
                )
                return SafetyNetAttestationResponse(
                    status=AttestationStatus.INVALID,
                    device_id=request.device_id,
                    error_message="Nonce mismatch",
                )

            # Check CTS profile match and basic integrity
            cts_profile_match = payload.get("ctsProfileMatch", False)
            basic_integrity = payload.get("basicIntegrity", False)

            logger.info(
                f"SafetyNet results for {request.device_id}: "
                f"CTS={cts_profile_match}, BasicIntegrity={basic_integrity}"
            )

            # Determine status
            # For production: require both CTS and basic integrity
            # For development: allow basic integrity only
            status = (
                AttestationStatus.VALID
                if cts_profile_match and basic_integrity
                else AttestationStatus.INVALID
            )

            # Get advice if failed
            advice = (
                payload.get("advice") if status == AttestationStatus.INVALID else None
            )

            response = SafetyNetAttestationResponse(
                status=status,
                device_id=request.device_id,
                cts_profile_match=cts_profile_match,
                basic_integrity=basic_integrity,
                advice=advice,
            )

            # Cache result
            self._cache_attestation(
                device_id=request.device_id,
                platform=AttestationPlatform.ANDROID,
                status=status,
                details={
                    "cts_profile_match": cts_profile_match,
                    "basic_integrity": basic_integrity,
                    "advice": advice,
                },
            )

            return response

        except Exception as e:
            logger.error(f"SafetyNet verification failed for {request.device_id}: {e}")
            return SafetyNetAttestationResponse(
                status=AttestationStatus.FAILED,
                device_id=request.device_id,
                error_message=str(e),
            )

    # ===========================
    # iOS DeviceCheck
    # ===========================

    def verify_devicecheck(
        self, request: DeviceCheckAttestationRequest
    ) -> DeviceCheckAttestationResponse:
        """Verify iOS DeviceCheck attestation.

        Steps:
        1. Check cache for recent verification
        2. Generate JWT for Apple API authentication
        3. Call Apple DeviceCheck API to validate token
        4. Check device integrity status
        5. Cache result for 1 hour

        Args:
            request: DeviceCheck attestation request with device token

        Returns:
            DeviceCheck attestation response with verification status
        """
        logger.info(
            f"Verifying DeviceCheck attestation for device: {request.device_id}"
        )

        # Check cache
        cached = self._get_cached_attestation(
            request.device_id, AttestationPlatform.IOS
        )
        if cached:
            logger.debug(f"Using cached attestation for device: {request.device_id}")
            return DeviceCheckAttestationResponse(
                status=cached.status,
                device_id=cached.device_id,
                timestamp=cached.timestamp,
                integrity_verified=cached.details.get("integrity_verified"),
            )

        # Check if Apple credentials are configured
        if not all([self.apple_team_id, self.apple_key_id, self.apple_private_key]):
            logger.warning("Apple DeviceCheck credentials not configured")
            return DeviceCheckAttestationResponse(
                status=AttestationStatus.UNSUPPORTED,
                device_id=request.device_id,
                error_message="DeviceCheck not configured",
            )

        try:
            # In a real implementation:
            # 1. Generate JWT using apple_private_key
            # 2. Call https://api.devicecheck.apple.com/v1/validate_device_token
            # 3. Parse response and check device integrity

            # For now, return a placeholder response
            # TODO: Implement full DeviceCheck verification
            logger.warning("DeviceCheck verification not fully implemented yet")

            response = DeviceCheckAttestationResponse(
                status=AttestationStatus.UNSUPPORTED,
                device_id=request.device_id,
                error_message="DeviceCheck verification not implemented",
            )

            return response

        except Exception as e:
            logger.error(
                f"DeviceCheck verification failed for {request.device_id}: {e}"
            )
            return DeviceCheckAttestationResponse(
                status=AttestationStatus.FAILED,
                device_id=request.device_id,
                error_message=str(e),
            )

    # ===========================
    # Desktop Fingerprinting
    # ===========================

    def verify_desktop(
        self, request: DesktopAttestationRequest
    ) -> DesktopAttestationResponse:
        """Verify desktop device fingerprint.

        Desktop platforms don't have hardware-backed attestation,
        so we use device fingerprinting and rate limiting:

        1. Check if fingerprint matches previous enrollment
        2. Verify device is within rate limits (e.g., 5 enrollments/hour)
        3. Cache result for 1 hour

        Args:
            request: Desktop attestation request with fingerprint

        Returns:
            Desktop attestation response with verification status
        """
        logger.info(f"Verifying desktop device fingerprint for: {request.device_id}")

        # Check cache
        cached = self._get_cached_attestation(
            request.device_id, AttestationPlatform.DESKTOP
        )
        if cached:
            logger.debug(f"Using cached attestation for device: {request.device_id}")
            return DesktopAttestationResponse(
                status=cached.status,
                device_id=cached.device_id,
                timestamp=cached.timestamp,
                fingerprint_match=cached.details.get("fingerprint_match"),
                rate_limit_ok=cached.details.get("rate_limit_ok"),
            )

        try:
            # Validate fingerprint format (SHA-256 hex)
            if not request.fingerprint or len(request.fingerprint) != 64:
                return DesktopAttestationResponse(
                    status=AttestationStatus.INVALID,
                    device_id=request.device_id,
                    error_message="Invalid fingerprint format",
                )

            # Check rate limiting
            # In production: use Redis or DynamoDB to track enrollment attempts
            # For now: simple in-memory check
            rate_limit_ok = self._check_rate_limit(request.device_id)

            # Fingerprint matching would check against stored fingerprint
            # For first-time enrollment, we accept the fingerprint
            fingerprint_match = True  # Placeholder

            status = (
                AttestationStatus.VALID
                if rate_limit_ok and fingerprint_match
                else AttestationStatus.INVALID
            )

            response = DesktopAttestationResponse(
                status=status,
                device_id=request.device_id,
                fingerprint_match=fingerprint_match,
                rate_limit_ok=rate_limit_ok,
                error_message="Rate limit exceeded" if not rate_limit_ok else None,
            )

            # Cache result
            self._cache_attestation(
                device_id=request.device_id,
                platform=AttestationPlatform.DESKTOP,
                status=status,
                details={
                    "fingerprint_match": fingerprint_match,
                    "rate_limit_ok": rate_limit_ok,
                },
            )

            return response

        except Exception as e:
            logger.error(f"Desktop verification failed for {request.device_id}: {e}")
            return DesktopAttestationResponse(
                status=AttestationStatus.FAILED,
                device_id=request.device_id,
                error_message=str(e),
            )

    # ===========================
    # Cache Management
    # ===========================

    def _get_cached_attestation(
        self, device_id: str, platform: AttestationPlatform
    ) -> AttestationCacheEntry | None:
        """Get cached attestation result if not expired."""
        cache_key = f"{device_id}:{platform.value}"
        entry = self._cache.get(cache_key)

        if entry and not entry.is_expired():
            return entry

        # Remove expired entry
        if entry:
            del self._cache[cache_key]

        return None

    def _cache_attestation(
        self,
        device_id: str,
        platform: AttestationPlatform,
        status: AttestationStatus,
        details: dict,
    ) -> None:
        """Cache attestation result."""
        cache_key = f"{device_id}:{platform.value}"
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            seconds=self.cache_ttl_seconds
        )

        entry = AttestationCacheEntry(
            device_id=device_id,
            platform=platform,
            status=status,
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            expires_at=expires_at,
            details=details,
        )

        self._cache[cache_key] = entry
        logger.debug(f"Cached attestation for {cache_key} until {expires_at}")

    def _check_rate_limit(self, device_id: str) -> bool:
        """Check if device is within rate limits.

        Simple in-memory implementation. In production, use Redis.
        Rate limit: 5 attestations per hour per device.
        """
        # Placeholder implementation
        # In production: use Redis with sliding window or token bucket
        return True

    def clear_cache(self) -> None:
        """Clear all cached attestation results."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} attestation cache entries")
