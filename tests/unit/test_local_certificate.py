"""Tests for local certificate repository implementation."""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from apuntador.infrastructure.implementations.local.certificate_repository import (
    LocalCertificateRepository,
)
from apuntador.infrastructure.repositories import Certificate

UTC = ZoneInfo("UTC")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path)


@pytest.fixture
def cert_repo(temp_dir):
    """Create a local certificate repository instance."""
    return LocalCertificateRepository(base_dir=str(temp_dir))


@pytest.fixture
def sample_certificate():
    """Create a sample certificate for testing."""
    return Certificate(
        serial="test-serial-123",
        device_id="device-123",
        platform="android",
        certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
        issued_at=datetime.now(UTC).replace(tzinfo=None),
        expires_at=(datetime.now(UTC) + timedelta(days=30)).replace(tzinfo=None),
        revoked=False,
    )


@pytest.mark.asyncio
async def test_save_and_get_certificate(cert_repo, sample_certificate):
    """Test saving and retrieving a certificate."""
    await cert_repo.save_certificate(sample_certificate)

    retrieved = await cert_repo.get_certificate(sample_certificate.device_id)

    assert retrieved is not None
    assert retrieved.device_id == sample_certificate.device_id
    assert retrieved.serial == sample_certificate.serial


@pytest.mark.asyncio
async def test_revoke_certificate(cert_repo, sample_certificate):
    """Test revoking a certificate."""
    await cert_repo.save_certificate(sample_certificate)

    result = await cert_repo.revoke_certificate(sample_certificate.device_id)

    assert result is True

    retrieved = await cert_repo.get_certificate(sample_certificate.device_id)
    assert retrieved.revoked is True


@pytest.mark.asyncio
async def test_revoke_nonexistent_certificate(cert_repo):
    """Test revoking a certificate that doesn't exist."""
    result = await cert_repo.revoke_certificate("nonexistent-device")

    assert result is False


@pytest.mark.asyncio
async def test_list_all_certificates(cert_repo):
    """Test listing all certificates."""
    cert1 = Certificate(
        serial="serial-1",
        device_id="device-1",
        platform="android",
        certificate_pem="-----BEGIN CERTIFICATE-----\ntest1\n-----END CERTIFICATE-----",
        issued_at=datetime.now(UTC).replace(tzinfo=None),
        expires_at=(datetime.now(UTC) + timedelta(days=30)).replace(tzinfo=None),
        revoked=False,
    )
    cert2 = Certificate(
        serial="serial-2",
        device_id="device-2",
        platform="ios",
        certificate_pem="-----BEGIN CERTIFICATE-----\ntest2\n-----END CERTIFICATE-----",
        issued_at=datetime.now(UTC).replace(tzinfo=None),
        expires_at=(datetime.now(UTC) + timedelta(days=60)).replace(tzinfo=None),
        revoked=False,
    )

    await cert_repo.save_certificate(cert1)
    await cert_repo.save_certificate(cert2)

    all_certs = await cert_repo.list_all_certificates()

    assert len(all_certs) == 2
    device_ids = {cert.device_id for cert in all_certs}
    assert "device-1" in device_ids
    assert "device-2" in device_ids


@pytest.mark.asyncio
async def test_find_expiring_certificates_excludes_revoked(cert_repo):
    """Test list_expiring_certificates excludes revoked certificates."""
    # Create active certificate expiring soon
    active_cert = Certificate(
        serial="ACTIVE-123",
        device_id="device-active",
        platform="android",
        certificate_pem=(
            "-----BEGIN CERTIFICATE-----\nactive\n"
            "-----END CERTIFICATE-----"
        ),
        issued_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=25),
        expires_at=(datetime.now(UTC) + timedelta(days=2)).replace(tzinfo=None),
        revoked=False,
    )

    # Create revoked certificate expiring soon
    revoked_cert = Certificate(
        serial="REVOKED-456",
        device_id="device-revoked",
        platform="ios",
        certificate_pem=(
            "-----BEGIN CERTIFICATE-----\nrevoked\n"
            "-----END CERTIFICATE-----"
        ),
        issued_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=25),
        expires_at=(datetime.now(UTC) + timedelta(days=2)).replace(tzinfo=None),
        revoked=True,
    )

    await cert_repo.save_certificate(active_cert)
    await cert_repo.save_certificate(revoked_cert)

    # Find certificates expiring in 3 days
    expiring = await cert_repo.list_expiring_certificates(days=3)

    # Should only include the active certificate
    assert len(expiring) == 1
    assert expiring[0].serial == "ACTIVE-123"
    assert expiring[0].revoked is False
