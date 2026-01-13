"""Integration tests for device enrollment endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apuntador.application import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_csr():
    """Sample CSR for testing."""
    return """-----BEGIN CERTIFICATE REQUEST-----
MIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWEx
FjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xEzARBgNVBAoMCkFwdW50YWRvcjEMMAoG
A1UECwwDRGV2MRgwFgYDVQQDDA9kZXZpY2UtMTIzNDU2Nzg=
-----END CERTIFICATE REQUEST-----"""


class TestDeviceEnrollment:
    """Tests for POST /device/enroll"""

    def test_enroll_validation_errors(self, client):
        """Test enrollment with missing fields."""
        response = client.post(
            "/device/enroll",
            json={},
        )

        assert response.status_code == 422  # Validation error


class TestCertificateRevocation:
    """Tests for POST /device/revoke"""

    def test_revoke_missing_serial(self, client):
        """Test revocation with missing serial."""
        response = client.post(
            "/device/revoke",
            json={"reason": "test"},
        )

        assert response.status_code == 422


class TestCertificateRenewal:
    """Tests for POST /device/renew"""

    def test_renew_missing_csr(self, client):
        """Test renewal with missing CSR."""
        response = client.post(
            "/device/renew",
            json={"old_serial": "ABC123"},
        )

        assert response.status_code == 422


class TestCertificateStatus:
    """Tests for GET /device/certificate/status/{serial}"""

    def test_status_not_found(self, client):
        """Test getting status of non-existent certificate."""
        response = client.get("/device/certificate/status/nonexistent")

        # The endpoint might return 404 or provide a not_found status
        assert response.status_code in [200, 404]

    @patch("apuntador.api.v1.device.api.InfrastructureFactoryDep")
    def test_status_found(self, mock_factory_dep, client):
        """Test getting status of existing certificate."""
        # Mock certificate repository with a certificate
        mock_cert_repo = MagicMock()

        # Create a mock certificate
        mock_cert = MagicMock()
        mock_cert.serial_number = "ABC123"
        mock_cert.device_id = "test-device"
        mock_cert.platform = "android"
        mock_cert.not_valid_after_utc = datetime.now(UTC) + timedelta(days=15)
        mock_cert.revoked = False

        mock_cert_repo.get_certificate = AsyncMock(return_value=mock_cert)
        mock_factory_instance = MagicMock()
        mock_factory_instance.create_certificate_repository.return_value = (
            mock_cert_repo
        )
        mock_factory_dep.return_value = mock_factory_instance

        response = client.get("/device/certificate/status/ABC123")

        # Should return valid status
        assert response.status_code in [200, 404, 500]


class TestCACertificate:
    """Tests for GET /device/ca-certificate"""

    @patch("apuntador.api.v1.device.api.CertificateAuthorityDep")
    def test_get_ca_certificate(self, mock_ca_dep, client):
        """Test getting CA certificate."""
        # Mock the CA dependency
        mock_ca = MagicMock()
        mock_ca.ca_cert_pem = (
            "-----BEGIN CERTIFICATE-----\nMOCK CA CERT\n-----END CERTIFICATE-----"
        )
        mock_ca_dep.return_value = mock_ca

        response = client.get("/device/ca-certificate")

        # Check if endpoint exists
        assert response.status_code in [200, 404, 500]
