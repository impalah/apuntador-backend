"""
Abstract interface for secrets storage (CA private key, etc).

Handles secure storage of sensitive cryptographic material:
- CA private key storage and retrieval
- Key rotation support
- Access logging
"""

from abc import ABC, abstractmethod


class SecretsRepository(ABC):
    """
    Abstract interface for secrets management operations.

    Implementations must provide secure storage for:
    - CA private key (PEM format)
    - CA certificate (PEM format)
    - Other sensitive configuration values
    """

    @abstractmethod
    async def get_ca_private_key(self) -> str:
        """
        Retrieve CA private key in PEM format.

        Returns:
            PEM-encoded CA private key

        Raises:
            Exception: If key not found or access denied
        """
        pass

    @abstractmethod
    async def store_ca_private_key(self, private_key_pem: str) -> None:
        """
        Store CA private key securely.

        Args:
            private_key_pem: PEM-encoded CA private key

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def get_ca_certificate(self) -> str:
        """
        Retrieve CA certificate in PEM format.

        Returns:
            PEM-encoded CA certificate

        Raises:
            Exception: If certificate not found
        """
        pass

    @abstractmethod
    async def store_ca_certificate(self, certificate_pem: str) -> None:
        """
        Store CA certificate.

        Args:
            certificate_pem: PEM-encoded CA certificate

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def get_secret(self, key: str) -> str | None:
        """
        Retrieve arbitrary secret by key.

        Args:
            key: Secret identifier

        Returns:
            Secret value if found, None otherwise
        """
        pass

    @abstractmethod
    async def store_secret(self, key: str, value: str) -> None:
        """
        Store arbitrary secret.

        Args:
            key: Secret identifier
            value: Secret value

        Raises:
            Exception: If storage operation fails
        """
        pass
