"""Tests for local secrets repository implementation."""

import pytest
from pathlib import Path
import tempfile
import shutil

from apuntador.infrastructure.implementations.local.secrets_repository import (
    LocalSecretsRepository,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path)


@pytest.fixture
def secrets_repo(temp_dir):
    """Create a local secrets repository instance."""
    return LocalSecretsRepository(base_dir=str(temp_dir))


@pytest.mark.asyncio
async def test_store_and_retrieve_secret(secrets_repo):
    """Test storing and retrieving a secret."""
    secret_id = "test-secret"
    secret_value = "super-secret-value"

    await secrets_repo.store_secret(secret_id, secret_value)
    retrieved = await secrets_repo.get_secret(secret_id)

    assert retrieved == secret_value


@pytest.mark.asyncio
async def test_get_nonexistent_secret(secrets_repo):
    """Test retrieving a secret that doesn't exist."""
    result = await secrets_repo.get_secret("nonexistent-secret")

    assert result is None


@pytest.mark.asyncio
async def test_update_secret(secrets_repo):
    """Test updating a secret."""
    secret_id = "update-me"
    secret_value = "original-value"
    new_value = "updated-value"

    await secrets_repo.store_secret(secret_id, secret_value)
    await secrets_repo.store_secret(secret_id, new_value)

    retrieved = await secrets_repo.get_secret(secret_id)
    assert retrieved == new_value


@pytest.mark.asyncio
async def test_multiple_secrets(secrets_repo):
    """Test storing and retrieving multiple secrets."""
    await secrets_repo.store_secret("secret-1", "value-1")
    await secrets_repo.store_secret("secret-2", "value-2")
    await secrets_repo.store_secret("secret-3", "value-3")

    val1 = await secrets_repo.get_secret("secret-1")
    val2 = await secrets_repo.get_secret("secret-2")
    val3 = await secrets_repo.get_secret("secret-3")

    assert val1 == "value-1"
    assert val2 == "value-2"
    assert val3 == "value-3"
