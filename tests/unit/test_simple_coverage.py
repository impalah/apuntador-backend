"""Simple tests to reach 80% coverage target."""

import pytest
from unittest.mock import patch


def test_di_get_oauth_service_googledrive():
    """Test getting OAuth service by provider name - Google Drive."""
    from apuntador.di import get_oauth_service
    from apuntador.config import get_settings

    settings = get_settings()

    service = get_oauth_service("googledrive", settings)

    assert service is not None
    assert service.provider_name == "googledrive"


def test_di_get_oauth_service_dropbox():
    """Test getting OAuth service by provider name - Dropbox."""
    from apuntador.di import get_oauth_service
    from apuntador.config import get_settings

    settings = get_settings()

    service = get_oauth_service("dropbox", settings)

    assert service is not None
    assert service.provider_name == "dropbox"


def test_di_get_oauth_service_invalid_provider():
    """Test getting OAuth service with invalid provider raises error."""
    from apuntador.di import get_oauth_service
    from apuntador.config import get_settings

    settings = get_settings()

    with pytest.raises(ValueError, match="Unsupported OAuth provider"):
        get_oauth_service("invalid_provider", settings)


def test_settings_enabled_providers_list():
    """Test getting enabled cloud providers list."""
    with patch.dict(
        "os.environ", {"ENABLED_CLOUD_PROVIDERS": "googledrive, dropbox, onedrive"}
    ):
        from apuntador.config import Settings

        settings = Settings()

        providers = settings.get_enabled_cloud_providers()

        assert "googledrive" in providers
        assert "dropbox" in providers
        assert "onedrive" in providers
        assert len(providers) == 3


def test_settings_enabled_providers_with_spaces():
    """Test enabled providers parsing handles extra spaces."""
    with patch.dict(
        "os.environ", {"ENABLED_CLOUD_PROVIDERS": "  googledrive ,  ,  dropbox  "}
    ):
        from apuntador.config import Settings

        settings = Settings()

        providers = settings.get_enabled_cloud_providers()

        # Should filter empty values and trim spaces
        assert "googledrive" in providers
        assert "dropbox" in providers
        assert "" not in providers


def test_settings_is_provider_enabled_case_handling():
    """Test provider enabled check is case-insensitive."""
    with patch.dict("os.environ", {"ENABLED_CLOUD_PROVIDERS": "GoogleDrive,DropBox"}):
        from apuntador.config import Settings

        settings = Settings()

        assert settings.is_provider_enabled("googledrive") is True
        assert settings.is_provider_enabled("GOOGLEDRIVE") is True
        assert settings.is_provider_enabled("GoogleDrive") is True
        assert settings.is_provider_enabled("dropbox") is True
        assert settings.is_provider_enabled("DROPBOX") is True


@pytest.mark.asyncio
async def test_infrastructure_factory_creates_all_repos():
    """Test infrastructure factory creates all repository types."""
    from apuntador.infrastructure import InfrastructureFactory
    from apuntador.config import get_settings

    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    # Create all three types
    cert_repo = factory.get_certificate_repository()
    secrets_repo = factory.get_secrets_repository()
    storage_repo = factory.get_storage_repository()

    # All should be created successfully
    assert cert_repo is not None
    assert secrets_repo is not None
    assert storage_repo is not None


def test_json_sink_initialization():
    """Test JsonSink can be initialized."""
    import io
    from apuntador.core.logging import JsonSink

    stream = io.StringIO()
    sink = JsonSink(stream=stream)

    assert sink is not None
    assert sink.stream == stream


def test_add_trace_id_returns_true():
    """Test add_trace_id filter always returns True."""
    from apuntador.core.logging import add_trace_id

    record = {"extra": {}}

    result = add_trace_id(record)

    # Should always return True to pass the filter
    assert result is True
    # Should add trace_id to extra
    assert "trace_id" in record["extra"]


def test_get_rfc_section_url_multiple_statuses():
    """Test RFC section URL generation for various status codes."""
    from apuntador.models.errors import get_rfc_section_url

    # Test known status codes
    url_400 = get_rfc_section_url(400)
    assert "6.5.1" in url_400

    url_404 = get_rfc_section_url(404)
    assert "6.5.4" in url_404

    url_500 = get_rfc_section_url(500)
    assert "6.6.1" in url_500

    # Test unknown status code defaults to 500 section
    url_unknown = get_rfc_section_url(999)
    assert "6.6.1" in url_unknown


def test_problem_detail_with_minimal_fields():
    """Test ProblemDetail can be created with minimal required fields."""
    from apuntador.models.errors import ProblemDetail

    error = ProblemDetail(
        title="Error",
        status=400,
        detail="Something went wrong",
    )

    assert error.title == "Error"
    assert error.status == 400
    # Type should have a default value
    assert error.type is not None
