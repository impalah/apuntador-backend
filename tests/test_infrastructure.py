"""
Unit tests for infrastructure repositories.

Tests the local file-based implementations.
"""

import shutil
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from apuntador.infrastructure.implementations.local import (
    LocalCertificateRepository,
    LocalSecretsRepository,
    LocalStorageRepository,
)
from apuntador.infrastructure.repositories import Certificate


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.mark.asyncio
class TestLocalCertificateRepository:
    """Tests for LocalCertificateRepository."""

    async def test_save_and_retrieve_certificate(self, temp_dir):
        """Test saving and retrieving a certificate."""
        repo = LocalCertificateRepository(base_dir=temp_dir)

        now = datetime.now(UTC).replace(tzinfo=None)
        cert = Certificate(
            device_id="test-device-001",
            serial="1234567890ABCDEF",
            platform="android",
            issued_at=now,
            expires_at=now + timedelta(days=30),
            certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            revoked=False,
        )

        await repo.save_certificate(cert)

        retrieved = await repo.get_certificate("test-device-001")

        assert retrieved is not None
        assert retrieved.device_id == cert.device_id
        assert retrieved.serial == cert.serial
        assert retrieved.platform == cert.platform
        assert not retrieved.revoked

    async def test_serial_whitelisting(self, temp_dir):
        """Test serial number whitelisting."""
        repo = LocalCertificateRepository(base_dir=temp_dir)

        now = datetime.now(UTC).replace(tzinfo=None)
        cert = Certificate(
            device_id="test-device-002",
            serial="FEDCBA0987654321",
            platform="ios",
            issued_at=now,
            expires_at=now + timedelta(days=30),
            certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            revoked=False,
        )

        await repo.save_certificate(cert)

        # Serial should be whitelisted
        assert await repo.is_serial_whitelisted("FEDCBA0987654321")

        # Unknown serial should not be whitelisted
        assert not await repo.is_serial_whitelisted("UNKNOWN")

    async def test_revoke_certificate(self, temp_dir):
        """Test certificate revocation."""
        repo = LocalCertificateRepository(base_dir=temp_dir)

        now = datetime.now(UTC).replace(tzinfo=None)
        cert = Certificate(
            device_id="test-device-003",
            serial="ABCD1234EFGH5678",
            platform="desktop",
            issued_at=now,
            expires_at=now + timedelta(days=7),
            certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            revoked=False,
        )

        await repo.save_certificate(cert)

        # Should be whitelisted initially
        assert await repo.is_serial_whitelisted("ABCD1234EFGH5678")

        # Revoke certificate
        revoked = await repo.revoke_certificate("test-device-003")
        assert revoked

        # Should no longer be whitelisted
        assert not await repo.is_serial_whitelisted("ABCD1234EFGH5678")

    async def test_list_expiring_certificates(self, temp_dir):
        """Test listing expiring certificates."""
        repo = LocalCertificateRepository(base_dir=temp_dir)

        now = datetime.now(UTC).replace(tzinfo=None)
        # Certificate expiring in 5 days
        cert1 = Certificate(
            device_id="expiring-soon",
            serial="EXPIRE001",
            platform="android",
            issued_at=now,
            expires_at=now + timedelta(days=5),
            certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            revoked=False,
        )

        # Certificate expiring in 20 days
        cert2 = Certificate(
            device_id="expiring-later",
            serial="EXPIRE002",
            platform="ios",
            issued_at=now,
            expires_at=now + timedelta(days=20),
            certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            revoked=False,
        )

        await repo.save_certificate(cert1)
        await repo.save_certificate(cert2)

        # List certificates expiring within 7 days
        expiring = await repo.list_expiring_certificates(days=7)

        assert len(expiring) == 1
        assert expiring[0].device_id == "expiring-soon"


@pytest.mark.asyncio
class TestLocalSecretsRepository:
    """Tests for LocalSecretsRepository."""

    async def test_store_and_retrieve_ca_private_key(self, temp_dir):
        """Test storing and retrieving CA private key."""
        repo = LocalSecretsRepository(base_dir=temp_dir)

        private_key = "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----"

        await repo.store_ca_private_key(private_key)
        retrieved = await repo.get_ca_private_key()

        assert retrieved == private_key

    async def test_store_and_retrieve_ca_certificate(self, temp_dir):
        """Test storing and retrieving CA certificate."""
        repo = LocalSecretsRepository(base_dir=temp_dir)

        certificate = (
            "-----BEGIN CERTIFICATE-----\ntest-cert\n-----END CERTIFICATE-----"
        )

        await repo.store_ca_certificate(certificate)
        retrieved = await repo.get_ca_certificate()

        assert retrieved == certificate

    async def test_store_and_retrieve_arbitrary_secret(self, temp_dir):
        """Test storing and retrieving arbitrary secrets."""
        repo = LocalSecretsRepository(base_dir=temp_dir)

        await repo.store_secret("api_key", "secret-value-123")
        retrieved = await repo.get_secret("api_key")

        assert retrieved == "secret-value-123"

    async def test_get_nonexistent_secret(self, temp_dir):
        """Test retrieving non-existent secret returns None."""
        repo = LocalSecretsRepository(base_dir=temp_dir)

        retrieved = await repo.get_secret("nonexistent")

        assert retrieved is None


@pytest.mark.asyncio
class TestLocalStorageRepository:
    """Tests for LocalStorageRepository."""

    async def test_upload_and_download_file(self, temp_dir):
        """Test file upload and download."""
        repo = LocalStorageRepository(base_dir=temp_dir)

        content = b"test file content"
        key = "test-file.txt"

        location = await repo.upload_file(key, content)

        assert location is not None

        downloaded = await repo.download_file(key)

        assert downloaded == content

    async def test_delete_file(self, temp_dir):
        """Test file deletion."""
        repo = LocalStorageRepository(base_dir=temp_dir)

        content = b"delete me"
        key = "to-delete.txt"

        await repo.upload_file(key, content)

        # File should exist
        assert await repo.file_exists(key)

        # Delete file
        deleted = await repo.delete_file(key)
        assert deleted

        # File should no longer exist
        assert not await repo.file_exists(key)

    async def test_get_public_url(self, temp_dir):
        """Test generating public URL."""
        repo = LocalStorageRepository(base_dir=temp_dir)

        content = b"public content"
        key = "public-file.txt"

        await repo.upload_file(key, content)

        url = await repo.get_public_url(key)

        assert url is not None
        assert url.startswith("file://")

    async def test_file_exists(self, temp_dir):
        """Test file existence check."""
        repo = LocalStorageRepository(base_dir=temp_dir)

        # Non-existent file
        assert not await repo.file_exists("nonexistent.txt")

        # Upload file
        await repo.upload_file("exists.txt", b"content")

        # Should now exist
        assert await repo.file_exists("exists.txt")
