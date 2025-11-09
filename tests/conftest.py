"""Global pytest configuration and fixtures for all tests.

CRITICAL: Environment variables MUST be set BEFORE importing any application code
because Pydantic Settings loads config at import time.
"""

import os

# Set test environment variables IMMEDIATELY, before any imports
# This ensures Pydantic Settings will load these values
_TEST_ENV_VARS = {
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

# Set environment variables NOW (at module import time)
for key, value in _TEST_ENV_VARS.items():
    os.environ.setdefault(key, value)

# Now it's safe to import pytest
import pytest  # noqa: E402
