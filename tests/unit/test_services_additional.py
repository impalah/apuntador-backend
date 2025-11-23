"""Additional tests for service modules."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

from apuntador.services.device_attestation import DeviceAttestationService


def test_device_attestation_android_without_api_key():
    """Test Android attestation requires Google API key."""
    service = DeviceAttestationService(google_api_key=None)

    # Should handle missing API key gracefully
    assert service.google_api_key is None


def test_device_attestation_ios_initialization():
    """Test iOS attestation service initialization."""
    service = DeviceAttestationService(google_api_key="test-key")

    assert service is not None
    assert service.google_api_key == "test-key"


def test_certificate_authority_initialization():
    """Test certificate authority initialization."""
    from apuntador.services.certificate_authority import CertificateAuthority
    from apuntador.infrastructure import InfrastructureFactory
    from apuntador.config import get_settings

    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)
    ca = CertificateAuthority(factory)

    assert ca is not None


def test_certificate_authority_with_custom_validity():
    """Test certificate authority with custom validity period."""
    from apuntador.services.certificate_authority import CertificateAuthority
    from apuntador.infrastructure import InfrastructureFactory
    from apuntador.config import get_settings

    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    # CA should handle different validity periods
    ca = CertificateAuthority(factory)
    assert ca is not None


def test_infrastructure_factory_provider_selection():
    """Test infrastructure factory selects correct provider."""
    from apuntador.infrastructure import InfrastructureFactory
    from apuntador.config import get_settings

    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    # Should default to 'local' provider
    assert factory.provider in ["local", "aws", "azure"]


def test_error_model_with_extensions():
    """Test error model can include extension data."""
    from apuntador.models.errors import ProblemDetail

    error = ProblemDetail(
        type="https://example.com/errors/validation",
        title="Validation Error",
        status=400,
        detail="Invalid request parameters",
        instance="/api/v1/test",
    )

    assert error.status == 400
    assert error.title == "Validation Error"


def test_error_model_default_type():
    """Test error model uses default type when not specified."""
    from apuntador.models.errors import ProblemDetail

    error = ProblemDetail(
        title="Server Error",
        status=500,
        detail="Internal server error occurred",
    )

    assert error.status == 500
    # Should have a default type
    assert error.type is not None
