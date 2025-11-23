"""Tests for additional coverage of infrastructure and core modules."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from apuntador.infrastructure.implementations.local.secrets_repository import (
    LocalSecretsRepository,
)
from apuntador.infrastructure.implementations.local.storage_repository import (
    LocalStorageRepository,
)


@pytest.mark.asyncio
async def test_secrets_repo_initialization():
    """Test secrets repository initialization creates directory."""
    repo = LocalSecretsRepository(base_dir="./test_secrets")

    assert repo.secrets_dir.exists()
    assert repo.base_dir.exists()


@pytest.mark.asyncio
async def test_storage_repo_file_url_generation(tmp_path):
    """Test storage repository generates file URLs."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    content = b"test data"
    key = "test_file.txt"

    result = await repo.upload_file(key, content)

    # Should return absolute path
    assert str(tmp_path) in result
    assert key in result


@pytest.mark.asyncio
async def test_storage_repo_nested_keys(tmp_path):
    """Test storage repository handles nested keys."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    content = b"nested content"
    key = "folder/subfolder/file.txt"

    result = await repo.upload_file(key, content)

    assert result is not None

    # Verify file was created in nested structure
    downloaded = await repo.download_file(key)
    assert downloaded == content


@pytest.mark.asyncio
async def test_storage_repo_download_after_delete(tmp_path):
    """Test downloading file after deletion returns None."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    content = b"to be deleted"
    key = "delete_test.txt"

    await repo.upload_file(key, content)
    await repo.delete_file(key)

    result = await repo.download_file(key)
    assert result is None


@pytest.mark.asyncio
async def test_secrets_repo_overwrite_secret(tmp_path):
    """Test overwriting existing secret."""
    repo = LocalSecretsRepository(base_dir=str(tmp_path))

    await repo.store_secret("my_key", "original_value")
    await repo.store_secret("my_key", "new_value")

    value = await repo.get_secret("my_key")
    assert value == "new_value"


@pytest.mark.asyncio
async def test_storage_repo_multiple_files(tmp_path):
    """Test storing and retrieving multiple files."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    files = {
        "file1.txt": b"content1",
        "file2.txt": b"content2",
        "file3.txt": b"content3",
    }

    for key, content in files.items():
        await repo.upload_file(key, content)

    for key, expected_content in files.items():
        actual_content = await repo.download_file(key)
        assert actual_content == expected_content


@pytest.mark.asyncio
async def test_storage_repo_binary_content(tmp_path):
    """Test storing and retrieving binary content."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    # Binary content with various byte values
    binary_content = bytes(range(256))
    key = "binary_file.bin"

    await repo.upload_file(key, binary_content, content_type="application/octet-stream")

    retrieved = await repo.download_file(key)
    assert retrieved == binary_content


@pytest.mark.asyncio
async def test_secrets_repo_empty_value(tmp_path):
    """Test storing empty secret value."""
    repo = LocalSecretsRepository(base_dir=str(tmp_path))

    await repo.store_secret("empty_key", "")

    value = await repo.get_secret("empty_key")
    assert value == ""


@pytest.mark.asyncio
async def test_storage_repo_get_file_url_nonexistent(tmp_path):
    """Test get_public_url returns None for nonexistent file."""
    repo = LocalStorageRepository(base_dir=str(tmp_path))

    # Try to get URL for file that doesn't exist
    url = await repo.get_public_url("nonexistent.txt")

    assert url is None
