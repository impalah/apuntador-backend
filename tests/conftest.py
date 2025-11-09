"""Global pytest configuration and fixtures for all tests."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def set_test_env_vars():
    """
    Set environment variables for testing.
    
    This fixture runs automatically before any tests and provides
    dummy OAuth credentials so tests don't fail due to missing configuration.
    
    These are NOT real credentials - just placeholders for testing.
    """
    # Store original values to restore after tests
    original_env = {}
    
    test_env_vars = {
        # Google Drive OAuth (dummy values for testing)
        "GOOGLE_CLIENT_ID": "test-google-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-test-secret-for-testing-only",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/oauth/callback/googledrive",
        
        # Dropbox OAuth (dummy values for testing)
        "DROPBOX_CLIENT_ID": "test-dropbox-client-id",
        "DROPBOX_CLIENT_SECRET": "test-dropbox-client-secret",
        "DROPBOX_REDIRECT_URI": "http://localhost:8000/oauth/callback/dropbox",
        
        # OneDrive OAuth (dummy values for testing)
        "ONEDRIVE_CLIENT_ID": "test-onedrive-client-id",
        "ONEDRIVE_CLIENT_SECRET": "test-onedrive-client-secret",
        "ONEDRIVE_REDIRECT_URI": "http://localhost:8000/oauth/callback/onedrive",
        
        # Server configuration
        "SECRET_KEY": "test-secret-key-minimum-32-characters-long-for-testing",
        "ENABLE_DOCS": "false",  # Keep docs disabled in tests
        
        # Infrastructure (use local for tests)
        "INFRASTRUCTURE_PROVIDER": "local",
        "SECRETS_PROVIDER": "local",
        "CERTIFICATE_DB_PROVIDER": "local",
        "STORAGE_PROVIDER": "local",
    }
    
    # Set test environment variables
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment after all tests
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
