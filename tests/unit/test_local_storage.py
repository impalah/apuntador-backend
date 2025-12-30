"""Tests for local storage repository implementation."""

import shutil
import tempfile
from pathlib import Path

import pytest

from apuntador.infrastructure.implementations.local.storage_repository import (
    LocalStorageRepository,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path)


@pytest.fixture
def storage_repo(temp_dir):
    """Create a local storage repository instance."""
    return LocalStorageRepository(base_dir=str(temp_dir))


@pytest.mark.asyncio
async def test_upload_file(storage_repo, temp_dir):
    """Test uploading a file."""
    content = b"test content"
    key = "test.txt"

    result = await storage_repo.upload_file(key, content)

    assert result is not None
    assert isinstance(result, str)
    file_path = storage_repo.storage_dir / key
    assert file_path.exists()
    assert file_path.read_bytes() == content


@pytest.mark.asyncio
async def test_download_file(storage_repo):
    """Test downloading a file."""
    content = b"download test"
    key = "download.txt"

    await storage_repo.upload_file(key, content)
    downloaded = await storage_repo.download_file(key)

    assert downloaded == content


@pytest.mark.asyncio
async def test_download_nonexistent_file(storage_repo):
    """Test downloading a file that doesn't exist."""
    result = await storage_repo.download_file("nonexistent.txt")
    assert result is None


@pytest.mark.asyncio
async def test_delete_file(storage_repo):
    """Test deleting a file."""
    content = b"to be deleted"
    key = "delete.txt"

    await storage_repo.upload_file(key, content)
    result = await storage_repo.delete_file(key)

    assert result is True
    file_path = storage_repo.storage_dir / key
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_file(storage_repo):
    """Test deleting a file that doesn't exist."""
    result = await storage_repo.delete_file("nonexistent.txt")
    assert result is False


@pytest.mark.asyncio
async def test_upload_with_content_type(storage_repo):
    """Test uploading a file with content type specified."""
    content = b"test content with type"
    key = "typed.txt"

    result = await storage_repo.upload_file(key, content, content_type="text/plain")

    assert result is not None
    assert isinstance(result, str)
