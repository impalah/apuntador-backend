"""
Local file-based storage repository implementation.

Stores files in a local directory structure:
    {base_dir}/
        storage/
            {key}

Generates file:// URLs for public access (development only).
"""

from pathlib import Path
from urllib.parse import quote

from loguru import logger

from apuntador.infrastructure.repositories.storage_repository import StorageRepository


class LocalStorageRepository(StorageRepository):
    """
    File-based storage for local development.

    Files are stored in a local directory with public access via file:// URLs.
    """

    def __init__(self, base_dir: str = "./.local_infrastructure/storage"):
        """
        Initialize local storage repository.

        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.storage_dir = self.base_dir / "storage"

        # Create directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized LocalStorageRepository at {self.base_dir}")

    def _file_path(self, key: str) -> Path:
        """
        Get path to storage file.

        Handles nested keys by creating subdirectories.
        """
        return self.storage_dir / key

    async def upload_file(
        self, key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file to local storage."""
        file_path = self._file_path(key)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_bytes(content)

        logger.info(f"Uploaded file: {key} ({len(content)} bytes)")

        return str(file_path.absolute())

    async def download_file(self, key: str) -> bytes | None:
        """Download file from local storage."""
        file_path = self._file_path(key)

        if not file_path.exists():
            return None

        return file_path.read_bytes()

    async def delete_file(self, key: str) -> bool:
        """Delete file from local storage."""
        file_path = self._file_path(key)

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info(f"Deleted file: {key}")

        return True

    async def get_public_url(self, key: str, expires_in: int = 3600) -> str | None:
        """
        Generate public URL for file access.

        For local storage, returns file:// URL (development only).
        expires_in parameter is ignored for local storage.
        """
        file_path = self._file_path(key)

        if not file_path.exists():
            return None

        # Generate file:// URL
        abs_path = file_path.absolute()
        url = f"file://{quote(str(abs_path))}"

        return url

    async def file_exists(self, key: str) -> bool:
        """Check if file exists."""
        file_path = self._file_path(key)
        return file_path.exists()
