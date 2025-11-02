"""
Abstract interface for file storage (truststore, CRLs, etc).

Handles storage of non-sensitive but important files:
- CA certificate bundle (truststore)
- Certificate Revocation Lists (CRLs)
- Attestation data backups
"""

from abc import ABC, abstractmethod


class StorageRepository(ABC):
    """
    Abstract interface for file storage operations.

    Implementations must provide:
    - File upload/download
    - Metadata tracking
    - Public URL generation (for truststore)
    """

    @abstractmethod
    async def upload_file(
        self, key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a file to storage.

        Args:
            key: File identifier/path
            content: File content as bytes
            content_type: MIME type of content

        Returns:
            Storage location identifier (URL or path)

        Raises:
            Exception: If upload fails
        """
        pass

    @abstractmethod
    async def download_file(self, key: str) -> bytes | None:
        """
        Download a file from storage.

        Args:
            key: File identifier/path

        Returns:
            File content as bytes if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: File identifier/path

        Returns:
            True if file was deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_public_url(self, key: str, expires_in: int = 3600) -> str | None:
        """
        Generate a public URL for file access.

        Args:
            key: File identifier/path
            expires_in: URL expiration in seconds (0 for permanent)

        Returns:
            Public URL if file exists, None otherwise
        """
        pass

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: File identifier/path

        Returns:
            True if file exists, False otherwise
        """
        pass
