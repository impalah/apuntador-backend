"""
Abstract interface for certificate storage and management.

Handles device certificate lifecycle:
- Storage of device certificates and metadata
- Serial number whitelisting
- Certificate lookup and validation
- Expiration tracking
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Certificate:
    """
    Device certificate metadata.

    Attributes:
        device_id: Unique device identifier
        serial: Certificate serial number (hex string)
        platform: Device platform (android, ios, desktop)
        issued_at: Certificate issue timestamp
        expires_at: Certificate expiration timestamp
        certificate_pem: PEM-encoded certificate
        revoked: Whether certificate has been revoked
    """

    device_id: str
    serial: str
    platform: str
    issued_at: datetime
    expires_at: datetime
    certificate_pem: str
    revoked: bool = False


class CertificateRepository(ABC):
    """
    Abstract interface for certificate storage operations.

    Implementations must provide thread-safe operations for:
    - Storing device certificates
    - Checking serial whitelist
    - Retrieving certificate metadata
    - Revoking certificates
    """

    @abstractmethod
    async def save_certificate(self, certificate: Certificate) -> None:
        """
        Store a device certificate.

        Args:
            certificate: Certificate metadata to store

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def get_certificate(self, device_id: str) -> Certificate | None:
        """
        Retrieve certificate by device ID.

        Args:
            device_id: Unique device identifier

        Returns:
            Certificate metadata if found, None otherwise
        """
        pass

    @abstractmethod
    async def is_serial_whitelisted(self, serial: str) -> bool:
        """
        Check if certificate serial is in whitelist.

        Args:
            serial: Certificate serial number (hex string)

        Returns:
            True if serial is whitelisted and not revoked, False otherwise
        """
        pass

    @abstractmethod
    async def revoke_certificate(self, device_id: str) -> bool:
        """
        Revoke a device certificate.

        Args:
            device_id: Device to revoke certificate for

        Returns:
            True if certificate was revoked, False if not found
        """
        pass

    @abstractmethod
    async def list_expiring_certificates(self, days: int) -> list[Certificate]:
        """
        List certificates expiring within specified days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of certificates expiring within the timeframe
        """
        pass

    @abstractmethod
    async def list_all_certificates(self) -> list[Certificate]:
        """
        List all stored certificates.

        Returns:
            List of all certificate metadata in the repository
        """
        pass
