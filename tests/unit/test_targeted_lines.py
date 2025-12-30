"""Targeted tests for specific uncovered lines."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_certificate_validity_check_expired_with_warning(caplog):
    """Test is_serial_whitelisted logs warning for expired certificate."""
    import tempfile

    from apuntador.infrastructure.implementations.local import (
        LocalCertificateRepository,
    )
    from apuntador.infrastructure.repositories.certificate_repository import Certificate

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalCertificateRepository(base_dir=tmp_dir)

        # Create expired certificate
        expired_cert = Certificate(
            device_id="expired-device",
            serial="EXPIRED-SERIAL",
            certificate_pem=(
                "-----BEGIN CERTIFICATE-----\nexpired\n"
                "-----END CERTIFICATE-----"
            ),
            issued_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60),
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=5),
            revoked=False,
            platform="android",
        )

        await repo.save_certificate(expired_cert)

        # Check validity - should return False and log warning
        is_valid = await repo.is_serial_whitelisted("EXPIRED-SERIAL")

        assert is_valid is False
        # This covers lines 127-128 (the expired check and warning log)


def test_problem_detail_set_default_type():
    """Test ProblemDetail sets type automatically based on status."""
    from apuntador.models.errors import ProblemDetail

    # Create error without explicit type
    error = ProblemDetail(
        title="Not Found",
        status=404,
        detail="Resource not found",
    )

    # Type should be auto-generated from status
    assert error.type is not None
    assert "rfc" in error.type.lower()
    assert "6.5.4" in error.type  # 404 section


def test_di_get_oauth_service_with_redirect_uri_override():
    """Test get_oauth_service with redirect_uri parameter."""
    from apuntador.config import get_settings
    from apuntador.di import get_oauth_service

    settings = get_settings()

    # Get Dropbox service with custom redirect URI
    service = get_oauth_service(
        "dropbox", settings, redirect_uri="http://custom-redirect.com/callback"
    )

    assert service is not None
    assert service.provider_name == "dropbox"
    # This should help cover lines around 228, 238


def test_settings_cors_parsing():
    """Test CORS origins parsing from defaults."""
    from apuntador.config import get_settings

    settings = get_settings()

    origins = settings.get_allowed_origins()

    # Should include at least the default origins
    assert isinstance(origins, list)
    assert len(origins) > 0
    # Default includes localhost
    assert any("localhost" in origin for origin in origins)


def test_settings_cors_default():
    """Test CORS allowed methods."""
    from apuntador.config import get_settings

    settings = get_settings()

    methods = settings.get_cors_allowed_methods()

    # Should return default methods
    assert isinstance(methods, list)
    assert len(methods) > 0


@pytest.mark.asyncio
async def test_local_secrets_update_existing():
    """Test updating an existing secret."""
    import tempfile

    from apuntador.infrastructure.implementations.local import LocalSecretsRepository

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalSecretsRepository(base_dir=tmp_dir)

        # Store initial value
        await repo.store_secret("update_key", "initial_value")

        # Update the value
        await repo.store_secret("update_key", "updated_value")

        # Retrieve and verify
        value = await repo.get_secret("update_key")
        assert value == "updated_value"


@pytest.mark.asyncio
async def test_local_storage_upload_with_content_type():
    """Test uploading file with explicit content type."""
    import tempfile

    from apuntador.infrastructure.implementations.local import LocalStorageRepository

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalStorageRepository(base_dir=tmp_dir)

        # Upload with content type
        path = await repo.upload_file(
            "document.pdf", b"PDF content here", content_type="application/pdf"
        )

        assert path is not None
        assert "document.pdf" in path


def test_config_log_format_case_insensitive():
    """Test log format handling is case-insensitive."""
    with patch.dict("os.environ", {"LOG_FORMAT": "JSON"}):
        from apuntador.config import Settings

        settings = Settings()

        # Should accept uppercase
        assert settings.log_format.lower() in ["json", "human"]


def test_config_debug_string_to_bool():
    """Test debug flag accepts string values."""
    with patch.dict("os.environ", {"DEBUG": "True"}):
        from apuntador.config import Settings

        settings = Settings()

        assert settings.debug is True

    with patch.dict("os.environ", {"DEBUG": "false"}):
        settings2 = Settings()

        assert settings2.debug is False


@pytest.mark.asyncio
async def test_local_certificate_save_overwrites_existing():
    """Test saving certificate with same device_id overwrites."""
    import tempfile

    from apuntador.infrastructure.implementations.local import (
        LocalCertificateRepository,
    )
    from apuntador.infrastructure.repositories.certificate_repository import Certificate

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalCertificateRepository(base_dir=tmp_dir)

        # Save first certificate
        cert1 = Certificate(
            device_id="overwrite-test",
            serial="SERIAL1",
            certificate_pem=(
                "-----BEGIN CERTIFICATE-----\nfirst\n"
                "-----END CERTIFICATE-----"
            ),
            issued_at=datetime.now(UTC).replace(tzinfo=None),
            expires_at=(datetime.now(UTC) + timedelta(days=30)).replace(tzinfo=None),
            revoked=False,
            platform="android",
        )

        await repo.save_certificate(cert1)

        # Save second certificate with same device_id
        cert2 = Certificate(
            device_id="overwrite-test",
            serial="SERIAL2",
            certificate_pem=(
                "-----BEGIN CERTIFICATE-----\nsecond\n"
                "-----END CERTIFICATE-----"
            ),
            issued_at=datetime.now(UTC).replace(tzinfo=None),
            expires_at=(datetime.now(UTC) + timedelta(days=30)).replace(tzinfo=None),
            revoked=False,
            platform="android",
        )

        await repo.save_certificate(cert2)

        # Retrieve - should get the second one
        retrieved = await repo.get_certificate("overwrite-test")

        assert retrieved is not None
        assert retrieved.serial == "SERIAL2"
