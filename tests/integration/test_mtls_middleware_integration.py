"""
Integration tests for mTLS validation middleware.

Tests the full request cycle with TestClient.
"""

import base64
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from apuntador.main import app


@pytest.fixture
def valid_certificate_pem():
    """Generate a valid X.509 certificate in PEM format."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Apuntador"),
            x509.NameAttribute(NameOID.COMMON_NAME, "android-testdevice123"),
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

    # Return PEM-encoded certificate and serial
    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    serial_hex = f"{cert.serial_number:x}"

    return pem_cert, serial_hex, cert


@pytest.fixture
def expired_certificate_pem():
    """Generate an expired X.509 certificate in PEM format."""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "android-expireddevice456"),
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

    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    serial_hex = f"{cert.serial_number:x}"

    return pem_cert, serial_hex, cert


class TestMTLSMiddlewareIntegration:
    """Integration tests for mTLS middleware with full app context."""

    def test_exempt_path_health_no_certificate(self):
        """Test that /health endpoint works without certificate."""
        client = TestClient(app)
        response = client.get("/health")

        # Should succeed without certificate
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_exempt_path_docs_no_certificate(self):
        """Test that /docs endpoint works without certificate (if enabled)."""
        client = TestClient(app)
        response = client.get("/docs")

        # Should succeed without certificate if docs are enabled
        # If docs are disabled (openapi_url=None), it will return 404
        assert response.status_code in [200, 404]

    def test_exempt_path_oauth_authorize_no_certificate(self):
        """Test that OAuth endpoints work without certificate."""
        client = TestClient(app)

        # Test authorize endpoint
        response = client.post(
            "/oauth/authorize/googledrive",
            json={
                "redirect_uri": "http://localhost:3000/callback",
                "state": "test-state",
            },
        )

        # Should succeed without certificate (OAuth endpoints are exempt)
        assert response.status_code in [200, 400, 422]  # 400/422 for validation errors

    def test_exempt_path_device_enrollment_no_certificate(self):
        """Test that device enrollment endpoint works without certificate."""
        client = TestClient(app)

        # Test enrollment endpoint (should be accessible without cert)
        response = client.post(
            "/device/enroll",
            json={
                "csr": "-----BEGIN CERTIFICATE REQUEST-----\ntest\n-----END CERTIFICATE REQUEST-----",
                "device_id": "test123",
                "platform": "android",
            },
        )

        # Should not fail due to missing certificate (will fail validation instead)
        assert response.status_code != 401  # Not "missing certificate" error

    def test_exempt_path_ca_certificate_no_certificate(self):
        """Test that CA certificate download works without certificate."""
        client = TestClient(app)

        # Test CA cert endpoint
        response = client.get("/device/ca-certificate")

        # Should succeed without certificate
        # Note: Will return 500 if CA not initialized, but NOT 401 (missing cert)
        assert response.status_code != 401

    def test_protected_endpoint_without_certificate(self):
        """Test that protected endpoints require certificate."""
        client = TestClient(app)

        # Test renewal endpoint (requires mTLS)
        response = client.post(
            "/device/renew",
            json={"csr": "test-csr", "device_id": "test123"},
        )

        # Should fail with 401 (missing certificate)
        assert response.status_code == 401
        response_data = response.json()
        assert (
            "certificate"
            in (
                response_data.get("message", "") + response_data.get("error", "")
            ).lower()
        )

    def test_protected_endpoint_with_valid_certificate(
        self, valid_certificate_pem, tmp_path
    ):
        """Test protected endpoint with valid certificate."""
        pem_cert, serial_hex, cert_obj = valid_certificate_pem

        # Create test client with temporary infrastructure
        # (In real scenario, certificate would be whitelisted during enrollment)
        client = TestClient(app)

        # Add certificate header (URL-encoded PEM)
        url_encoded_cert = pem_cert.replace("\n", "%0A")
        headers = {"X-Client-Cert": url_encoded_cert}

        # Test protected endpoint
        response = client.post(
            "/device/renew",
            json={"csr": "test-csr", "device_id": "testdevice123"},
            headers=headers,
        )

        # Will fail with 403 (certificate not whitelisted) instead of 401 (no cert)
        # This is expected - we're testing the middleware extracts the cert correctly
        assert response.status_code in [403, 404, 422]
        # 403 = not whitelisted
        # 404 = endpoint might not exist yet
        # 422 = validation error

    def test_protected_endpoint_with_expired_certificate(self, expired_certificate_pem):
        """Test protected endpoint with expired certificate."""
        pem_cert, serial_hex, cert_obj = expired_certificate_pem

        client = TestClient(app)

        # Add expired certificate header
        headers = {"X-Client-Cert": pem_cert}

        # Test protected endpoint
        response = client.post(
            "/device/renew",
            json={"csr": "test-csr", "device_id": "expireddevice456"},
            headers=headers,
        )

        # Should fail with 403 (certificate expired/invalid)
        assert response.status_code == 403
        response_data = response.json()
        # Check for error in message or reason field
        error_text = (
            response_data.get("message", "") + response_data.get("reason", "")
        ).lower()
        assert "expired" in error_text or "not whitelisted" in error_text

    def test_certificate_header_formats(self, valid_certificate_pem):
        """Test that middleware accepts multiple certificate header formats."""
        pem_cert, serial_hex, cert_obj = valid_certificate_pem
        client = TestClient(app)

        # Test X-Client-Cert (AWS API Gateway)
        headers_aws = {"X-Client-Cert": pem_cert.replace("\n", "%0A")}
        response_aws = client.post(
            "/device/renew",
            json={"csr": "test", "device_id": "test"},
            headers=headers_aws,
        )
        # Should not be 401 (cert extracted successfully)
        assert response_aws.status_code != 401

        # Test X-SSL-Client-Cert (Nginx)
        headers_nginx = {"X-SSL-Client-Cert": pem_cert}
        response_nginx = client.post(
            "/device/renew",
            json={"csr": "test", "device_id": "test"},
            headers=headers_nginx,
        )
        assert response_nginx.status_code != 401

        # Test X-Forwarded-Client-Cert (Envoy)
        der_cert = cert_obj.public_bytes(serialization.Encoding.DER)
        b64_cert = base64.b64encode(der_cert).decode("utf-8")
        envoy_header = f'Cert="{b64_cert}"'
        headers_envoy = {"X-Forwarded-Client-Cert": envoy_header}
        response_envoy = client.post(
            "/device/renew",
            json={"csr": "test", "device_id": "test"},
            headers=headers_envoy,
        )
        assert response_envoy.status_code != 401

    def test_malformed_certificate_header(self):
        """Test that middleware handles malformed certificate gracefully."""
        client = TestClient(app)

        # Send malformed certificate
        headers = {"X-Client-Cert": "not-a-valid-certificate"}

        response = client.post(
            "/device/renew",
            json={"csr": "test", "device_id": "test"},
            headers=headers,
        )

        # Should fail with 401 or 403 (cannot parse certificate)
        assert response.status_code in [401, 403]
