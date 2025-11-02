"""Integration tests for device attestation endpoints."""

import pytest
from fastapi.testclient import TestClient

from apuntador.application import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


class TestAndroidAttestation:
    """Tests for POST /api/device/attest/android"""

    def test_android_attestation_validation(self, client):
        """Test Android attestation with missing fields."""
        response = client.post(
            "/api/device/attest/android",
            json={},
        )

        assert response.status_code == 422  # Validation error


class TestIOSAttestation:
    """Tests for POST /api/device/attest/ios"""

    def test_ios_attestation_validation(self, client):
        """Test iOS attestation with missing fields."""
        response = client.post(
            "/api/device/attest/ios",
            json={},
        )

        assert response.status_code == 422  # Validation error


class TestDesktopAttestation:
    """Tests for POST /api/device/attest/desktop"""

    def test_desktop_attestation_validation(self, client):
        """Test Desktop attestation with missing fields."""
        response = client.post(
            "/api/device/attest/desktop",
            json={},
        )

        assert response.status_code == 422  # Validation error
