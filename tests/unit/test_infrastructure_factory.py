"""Tests for infrastructure factory."""

import pytest
from unittest.mock import patch

from apuntador.infrastructure import InfrastructureFactory
from apuntador.config import get_settings


def test_factory_creates_local_repositories():
    """Test factory creates local implementations by default."""
    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    cert_repo = factory.get_certificate_repository()
    secrets_repo = factory.get_secrets_repository()
    storage_repo = factory.get_storage_repository()

    assert cert_repo is not None
    assert secrets_repo is not None
    assert storage_repo is not None

    # Should be local implementations
    from apuntador.infrastructure.implementations.local import (
        LocalCertificateRepository,
        LocalSecretsRepository,
        LocalStorageRepository,
    )

    assert isinstance(cert_repo, LocalCertificateRepository)
    assert isinstance(secrets_repo, LocalSecretsRepository)
    assert isinstance(storage_repo, LocalStorageRepository)


def test_factory_with_different_providers():
    """Test factory handles different provider configurations."""
    # Test with local provider
    with patch.dict("os.environ", {"INFRASTRUCTURE_PROVIDER": "local"}):
        from apuntador.config import Settings

        settings = Settings()
        factory = InfrastructureFactory.from_settings(settings)

        assert factory.provider == "local"


def test_factory_provider_validation():
    """Test factory validates provider names."""
    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    # Provider should be one of the valid options
    assert factory.provider in ["local", "aws", "azure"]


@pytest.mark.asyncio
async def test_local_secrets_repo_get_nonexistent():
    """Test getting nonexistent secret returns None."""
    from apuntador.infrastructure.implementations.local import LocalSecretsRepository

    repo = LocalSecretsRepository()

    secret = await repo.get_secret("nonexistent-key-12345")

    assert secret is None


@pytest.mark.asyncio
async def test_local_storage_repo_delete_nonexistent():
    """Test deleting nonexistent file returns False."""
    from apuntador.infrastructure.implementations.local import LocalStorageRepository
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalStorageRepository(base_dir=tmp_dir)

        result = await repo.delete_file("nonexistent-file.txt")

        assert result is False


@pytest.mark.asyncio
async def test_local_storage_repo_file_exists():
    """Test file_exists method."""
    from apuntador.infrastructure.implementations.local import LocalStorageRepository
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalStorageRepository(base_dir=tmp_dir)

        # File doesn't exist
        exists = await repo.file_exists("test.txt")
        assert exists is False

        # Create file
        await repo.upload_file("test.txt", b"content")

        # Now it exists
        exists = await repo.file_exists("test.txt")
        assert exists is True


def test_settings_cors_methods_parsing():
    """Test CORS methods parsing."""
    with patch.dict("os.environ", {"CORS_ALLOWED_METHODS": "GET,POST,PUT,DELETE"}):
        from apuntador.config import Settings

        settings = Settings()

        methods = settings.get_cors_allowed_methods()

        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert len(methods) == 4


def test_settings_cors_headers_parsing():
    """Test CORS headers parsing."""
    with patch.dict(
        "os.environ", {"CORS_ALLOWED_HEADERS": "Content-Type,Authorization,X-Custom"}
    ):
        from apuntador.config import Settings

        settings = Settings()

        headers = settings.get_cors_allowed_headers()

        assert "Content-Type" in headers
        assert "Authorization" in headers
        assert "X-Custom" in headers
        assert len(headers) == 3
