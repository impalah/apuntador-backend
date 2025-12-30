"""Tests for Settings methods (CORS and provider helpers)."""

from unittest.mock import patch

from apuntador.config import Settings


def test_get_cors_allowed_methods_wildcard():
    """Test CORS methods returns wildcard list when set to '*'."""
    with patch.dict("os.environ", {"CORS_ALLOWED_METHODS": "*"}):
        settings = Settings()
        methods = settings.get_cors_allowed_methods()
        assert methods == ["*"]


def test_get_cors_allowed_methods_list():
    """Test CORS methods returns parsed list."""
    with patch.dict("os.environ", {"CORS_ALLOWED_METHODS": "GET, POST, PUT"}):
        settings = Settings()
        methods = settings.get_cors_allowed_methods()
        assert methods == ["GET", "POST", "PUT"]


def test_get_cors_allowed_headers_wildcard():
    """Test CORS headers returns wildcard list when set to '*'."""
    with patch.dict("os.environ", {"CORS_ALLOWED_HEADERS": "*"}):
        settings = Settings()
        headers = settings.get_cors_allowed_headers()
        assert headers == ["*"]


def test_get_cors_allowed_headers_list():
    """Test CORS headers returns parsed list."""
    with patch.dict(
        "os.environ", {"CORS_ALLOWED_HEADERS": "Authorization, Content-Type"}
    ):
        settings = Settings()
        headers = settings.get_cors_allowed_headers()
        assert headers == ["Authorization", "Content-Type"]


def test_get_enabled_cloud_providers():
    """Test getting list of enabled cloud providers."""
    with patch.dict("os.environ", {"ENABLED_CLOUD_PROVIDERS": "googledrive, dropbox"}):
        settings = Settings()
        providers = settings.get_enabled_cloud_providers()
        assert "googledrive" in providers
        assert "dropbox" in providers


def test_get_enabled_cloud_providers_empty_values():
    """Test filtering empty values in provider list."""
    with patch.dict(
        "os.environ", {"ENABLED_CLOUD_PROVIDERS": "googledrive,, ,dropbox"}
    ):
        settings = Settings()
        providers = settings.get_enabled_cloud_providers()
        assert providers == ["googledrive", "dropbox"]


def test_is_provider_enabled_true():
    """Test checking if provider is enabled returns True."""
    with patch.dict("os.environ", {"ENABLED_CLOUD_PROVIDERS": "googledrive, dropbox"}):
        settings = Settings()
        assert settings.is_provider_enabled("googledrive") is True
        assert settings.is_provider_enabled("dropbox") is True


def test_is_provider_enabled_false():
    """Test checking if provider is enabled returns False."""
    with patch.dict("os.environ", {"ENABLED_CLOUD_PROVIDERS": "googledrive"}):
        settings = Settings()
        assert settings.is_provider_enabled("onedrive") is False


def test_is_provider_enabled_case_insensitive():
    """Test provider check is case-insensitive."""
    with patch.dict("os.environ", {"ENABLED_CLOUD_PROVIDERS": "GoogleDrive"}):
        settings = Settings()
        assert settings.is_provider_enabled("GOOGLEDRIVE") is True
        assert settings.is_provider_enabled("googledrive") is True
