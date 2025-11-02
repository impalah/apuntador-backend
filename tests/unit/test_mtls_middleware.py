"""
Unit tests for mTLS validation middleware.

Tests certificate extraction, validation logic, and exempt paths.
"""

import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import Request
from starlette.datastructures import Headers

from apuntador.middleware.mtls_validation import MTLSValidationMiddleware


@pytest.fixture
def mock_infrastructure_factory():
    """Mock infrastructure factory."""
    factory = MagicMock()
    cert_repo = AsyncMock()
    factory.get_certificate_repository.return_value = cert_repo
    return factory, cert_repo


@pytest.fixture
def valid_certificate():
    """Generate a valid X.509 certificate for testing."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Apuntador"),
            x509.NameAttribute(NameOID.COMMON_NAME, "android-device123"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=30))
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    return cert


@pytest.fixture
def expired_certificate():
    """Generate an expired X.509 certificate for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "android-device456"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=60))
        .not_valid_after(datetime.now(UTC) - timedelta(days=30))
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    return cert


class TestMTLSValidationMiddleware:
    """Test mTLS validation middleware."""

    def test_exempt_paths(self, mock_infrastructure_factory):
        """Test that exempt paths are correctly identified."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Public endpoints should be exempt
        assert middleware._is_exempt_path("/")
        assert middleware._is_exempt_path("/health")
        assert middleware._is_exempt_path("/docs")
        assert middleware._is_exempt_path("/redoc")
        assert middleware._is_exempt_path("/openapi.json")

        # OAuth endpoints should be exempt
        assert middleware._is_exempt_path("/api/oauth/authorize/googledrive")
        assert middleware._is_exempt_path("/api/oauth/callback/dropbox")
        assert middleware._is_exempt_path("/api/oauth/token/refresh/googledrive")

        # Device enrollment should be exempt
        assert middleware._is_exempt_path("/api/device/enroll")
        assert middleware._is_exempt_path("/api/device/ca-certificate")

        # Protected endpoints should NOT be exempt
        assert not middleware._is_exempt_path("/api/device/renew")
        assert not middleware._is_exempt_path("/api/device/certificate/test123")
        assert not middleware._is_exempt_path("/api/protected/data")

    def test_extract_certificate_from_x_client_cert(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test certificate extraction from X-Client-Cert header."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Encode certificate as PEM
        pem_cert = valid_certificate.public_bytes(serialization.Encoding.PEM).decode(
            "utf-8"
        )

        # URL-encode the PEM (simulating AWS API Gateway)
        url_encoded = pem_cert.replace("\n", "%0A")

        # Create mock request
        headers = Headers({"x-client-cert": url_encoded})
        request = MagicMock(spec=Request)
        request.headers = headers

        # Extract certificate (should return PEM string)
        extracted_pem = middleware._extract_certificate(request)

        assert extracted_pem is not None
        assert "-----BEGIN CERTIFICATE-----" in extracted_pem
        assert "-----END CERTIFICATE-----" in extracted_pem

    def test_extract_certificate_from_x_ssl_client_cert(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test certificate extraction from X-SSL-Client-Cert header (Nginx)."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Encode certificate as PEM
        pem_cert = valid_certificate.public_bytes(serialization.Encoding.PEM).decode(
            "utf-8"
        )

        # Create mock request
        headers = Headers({"x-ssl-client-cert": pem_cert})
        request = MagicMock(spec=Request)
        request.headers = headers

        # Extract certificate (should return PEM string)
        extracted_pem = middleware._extract_certificate(request)

        assert extracted_pem is not None
        assert "-----BEGIN CERTIFICATE-----" in extracted_pem
        assert "-----END CERTIFICATE-----" in extracted_pem

    def test_extract_certificate_from_x_forwarded_client_cert(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test certificate extraction from X-Forwarded-Client-Cert header (Envoy)."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Encode certificate as base64 (simulating Envoy format)
        der_cert = valid_certificate.public_bytes(serialization.Encoding.DER)
        b64_cert = base64.b64encode(der_cert).decode("utf-8")

        # Envoy format: Cert="base64-cert"
        envoy_header = f'Cert="{b64_cert}"'

        # Create mock request
        headers = Headers({"x-forwarded-client-cert": envoy_header})
        request = MagicMock(spec=Request)
        request.headers = headers

        # Extract certificate (should return PEM string)
        extracted_pem = middleware._extract_certificate(request)

        assert extracted_pem is not None
        assert "-----BEGIN CERTIFICATE-----" in extracted_pem
        assert "-----END CERTIFICATE-----" in extracted_pem

    def test_extract_certificate_no_header(self, mock_infrastructure_factory):
        """Test certificate extraction when no header is present."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Create mock request with no cert headers
        headers = Headers({})
        request = MagicMock(spec=Request)
        request.headers = headers

        # Should return None
        extracted_cert = middleware._extract_certificate(request)
        assert extracted_cert is None

    @pytest.mark.asyncio
    async def test_validate_certificate_valid(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test validation of a valid certificate."""
        factory, cert_repo = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Convert certificate to PEM
        pem_cert = valid_certificate.public_bytes(serialization.Encoding.PEM).decode(
            "utf-8"
        )
        serial_hex = f"{valid_certificate.serial_number:x}"

        # Mock whitelist check and certificate lookup
        cert_repo.is_serial_whitelisted.return_value = True

        # Mock Certificate object from repository
        from datetime import datetime, timedelta

        from apuntador.infrastructure.repositories.certificate_repository import (
            Certificate,
        )

        mock_stored_cert = Certificate(
            device_id="device123",
            serial=serial_hex,
            platform="android",
            issued_at=datetime.now(UTC) - timedelta(days=1),
            expires_at=datetime.now(UTC) + timedelta(days=29),
            certificate_pem=pem_cert,
            revoked=False,
        )

        cert_repo.list_all_certificates.return_value = [mock_stored_cert]

        # Validate
        result = await middleware._validate_certificate(pem_cert)

        assert result["valid"] is True
        assert result["device_id"] == "device123"
        assert (
            result["serial"].upper() == serial_hex.upper()
        )  # Compare case-insensitive

    @pytest.mark.asyncio
    async def test_validate_certificate_not_whitelisted(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test validation fails when certificate is not whitelisted."""
        factory, cert_repo = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Convert certificate to PEM
        pem_cert = valid_certificate.public_bytes(serialization.Encoding.PEM).decode(
            "utf-8"
        )

        # Mock whitelist check to return False
        cert_repo.is_serial_whitelisted.return_value = False

        # Validate
        result = await middleware._validate_certificate(pem_cert)

        assert result["valid"] is False
        assert "not whitelisted" in result["reason"]

    @pytest.mark.asyncio
    async def test_validate_certificate_expired(
        self, mock_infrastructure_factory, expired_certificate
    ):
        """Test validation fails for expired certificate."""
        factory, cert_repo = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # Convert certificate to PEM
        pem_cert = expired_certificate.public_bytes(serialization.Encoding.PEM).decode(
            "utf-8"
        )
        serial_hex = f"{expired_certificate.serial_number:x}"

        # Mock whitelist check (certificate would be whitelisted)
        cert_repo.is_serial_whitelisted.return_value = True

        # Mock Certificate object from repository
        from datetime import datetime, timedelta

        from apuntador.infrastructure.repositories.certificate_repository import (
            Certificate,
        )

        mock_stored_cert = Certificate(
            device_id="device456",
            serial=serial_hex,
            platform="android",
            issued_at=datetime.now(UTC) - timedelta(days=60),
            expires_at=datetime.now(UTC) - timedelta(days=30),
            certificate_pem=pem_cert,
            revoked=False,
        )

        cert_repo.list_all_certificates.return_value = [mock_stored_cert]

        # Validate
        result = await middleware._validate_certificate(pem_cert)

        # Should fail due to expiration
        assert result["valid"] is False
        assert "expired" in result["reason"].lower()

    def test_extract_device_id_from_common_name(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test extracting device_id from certificate CN."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # CN format: "platform-deviceid"
        device_id = None
        for attribute in valid_certificate.subject:
            if attribute.oid == NameOID.COMMON_NAME:
                cn = attribute.value
                if "-" in cn:
                    device_id = cn.split("-", 1)[1]

        assert device_id == "device123"

    def test_extract_platform_from_common_name(
        self, mock_infrastructure_factory, valid_certificate
    ):
        """Test extracting platform from certificate CN."""
        factory, _ = mock_infrastructure_factory
        middleware = MTLSValidationMiddleware(
            app=MagicMock(), infrastructure_factory=factory
        )

        # CN format: "platform-deviceid"
        platform = None
        for attribute in valid_certificate.subject:
            if attribute.oid == NameOID.COMMON_NAME:
                cn = attribute.value
                if "-" in cn:
                    platform = cn.split("-", 1)[0]

        assert platform == "android"
