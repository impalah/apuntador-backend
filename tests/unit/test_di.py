"""Tests for dependency injection container."""

import pytest
from apuntador.di import (
    get_infrastructure_factory,
    get_certificate_authority,
    get_device_attestation_service,
    get_google_drive_service,
    get_dropbox_service,
)
from apuntador.config import get_settings
from apuntador.infrastructure import InfrastructureFactory
from apuntador.services.certificate_authority import CertificateAuthority
from apuntador.services.device_attestation import DeviceAttestationService


def test_get_infrastructure_factory():
    """Test getting infrastructure factory with settings."""
    settings = get_settings()
    factory = get_infrastructure_factory(settings)

    assert factory is not None
    assert isinstance(factory, InfrastructureFactory)


def test_get_certificate_authority():
    """Test getting certificate authority with factory."""
    settings = get_settings()
    factory = get_infrastructure_factory(settings)
    ca = get_certificate_authority(factory)

    assert ca is not None
    assert isinstance(ca, CertificateAuthority)


def test_get_device_attestation_service():
    """Test getting device attestation service with settings."""
    settings = get_settings()
    service = get_device_attestation_service(settings)

    assert service is not None
    assert isinstance(service, DeviceAttestationService)


def test_get_google_drive_service():
    """Test getting Google Drive service."""
    settings = get_settings()
    service = get_google_drive_service(settings)

    assert service is not None
    assert service.provider_name == "googledrive"


def test_get_dropbox_service():
    """Test getting Dropbox service."""
    settings = get_settings()
    service = get_dropbox_service(settings)

    assert service is not None
    assert service.provider_name == "dropbox"


def test_factory_creates_repositories():
    """Test that factory creates repository instances."""
    settings = get_settings()
    factory = get_infrastructure_factory(settings)

    cert_repo = factory.get_certificate_repository()
    assert cert_repo is not None

    secrets_repo = factory.get_secrets_repository()
    assert secrets_repo is not None

    storage_repo = factory.get_storage_repository()
    assert storage_repo is not None


def test_google_drive_service_scopes():
    """Test Google Drive service has correct scopes."""
    settings = get_settings()
    service = get_google_drive_service(settings)

    scopes = service.scopes
    assert len(scopes) > 0
    assert any("drive" in scope for scope in scopes)


def test_dropbox_service_scopes():
    """Test Dropbox service has correct scopes."""
    settings = get_settings()
    service = get_dropbox_service(settings)

    scopes = service.scopes
    assert len(scopes) > 0
    assert any("files" in scope for scope in scopes)


def test_google_drive_service_missing_credentials():
    """Test Google Drive service raises error with missing credentials."""
    from unittest.mock import Mock

    # Mock settings with missing credentials
    mock_settings = Mock()
    mock_settings.google_client_id = None
    mock_settings.google_client_secret = "secret"

    with pytest.raises(
        ValueError, match="Google Drive OAuth credentials not configured"
    ):
        get_google_drive_service(mock_settings)


def test_dropbox_service_missing_credentials():
    """Test Dropbox service raises error with missing credentials."""
    from unittest.mock import Mock

    # Mock settings with missing credentials
    mock_settings = Mock()
    mock_settings.dropbox_client_id = None

    with pytest.raises(ValueError, match="Dropbox OAuth credentials not configured"):
        get_dropbox_service(mock_settings)
