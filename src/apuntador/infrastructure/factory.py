"""
Infrastructure factory for provider selection.

Selects appropriate repository implementations based on configuration:
- local: File-based storage for development
- aws: DynamoDB, S3, Secrets Manager
- azure: CosmosDB, Blob Storage, Key Vault (future)

Usage:
    from apuntador.infrastructure import InfrastructureFactory
    from apuntador.config import get_settings

    # Option 1: From settings
    settings = get_settings()
    factory = InfrastructureFactory.from_settings(settings)

    # Option 2: Manual configuration
    factory = InfrastructureFactory(provider="local")

    # Get repositories
    cert_repo = factory.get_certificate_repository()
    secrets_repo = factory.get_secrets_repository()
    storage_repo = factory.get_storage_repository()
"""

from typing import TYPE_CHECKING, Literal

from loguru import logger

from apuntador.infrastructure.repositories import (
    CertificateRepository,
    SecretsRepository,
    StorageRepository,
)

if TYPE_CHECKING:
    from apuntador.config import Settings

InfrastructureProvider = Literal["local", "aws", "azure"]

# Error messages
AZURE_NOT_IMPLEMENTED_ERROR = "Azure provider not yet implemented"


class InfrastructureFactory:
    """
    Factory for creating infrastructure repository instances.

    Provides dependency injection for cloud-agnostic operations.
    """

    def __init__(self, provider: InfrastructureProvider | None = None, **config):
        """
        Initialize infrastructure factory.

        Args:
            provider: Infrastructure provider ("local", "aws", "azure")
                     If None, uses "local" as default.
            **config: Provider-specific configuration options
                     For backward compatibility, accepts legacy config like base_dir.

        Raises:
            ValueError: If provider is not supported

        Legacy usage (deprecated):
            factory = InfrastructureFactory(base_dir="/path/to/certs")
            # Automatically uses provider="local"

        Modern usage:
            factory = InfrastructureFactory(
                provider="aws",
                aws_region="us-west-2",
                dynamodb_table="certs",
                s3_bucket="bucket",
                secrets_prefix="app"
            )
        """
        # Handle legacy usage: InfrastructureFactory(base_dir=...)
        # Default to local provider if not specified
        if provider is None:
            provider = "local"

        self.provider = provider
        self.config = config

        logger.info(f"Initialized InfrastructureFactory with provider: {provider}")

    @classmethod
    def from_settings(cls, settings: "Settings") -> "InfrastructureFactory":
        """
        Create factory from Settings object.

        Args:
            settings: Application settings from config.py

        Returns:
            InfrastructureFactory configured from settings

        Usage:
            from apuntador.config import get_settings
            settings = get_settings()
            factory = InfrastructureFactory.from_settings(settings)
        """
        config = {
            "base_dir": settings.infrastructure_base_dir,
            "aws_region": settings.aws_region,
            "dynamodb_table": settings.aws_dynamodb_table,
            "s3_bucket": settings.aws_s3_bucket,
            "secrets_prefix": settings.aws_secrets_prefix,
            "auto_create_resources": settings.auto_create_resources,
        }

        return cls(provider=settings.infrastructure_provider, **config)

    def get_certificate_repository(self) -> CertificateRepository:
        """
        Get certificate repository for configured provider.

        Returns:
            CertificateRepository implementation

        Raises:
            ValueError: If provider is not supported
        """
        if self.provider == "local":
            from apuntador.infrastructure.implementations.local import (
                LocalCertificateRepository,
            )

            base_dir = self.config.get(
                "base_dir", "./.local_infrastructure/certificates"
            )
            return LocalCertificateRepository(base_dir=base_dir)

        elif self.provider == "aws":
            from apuntador.infrastructure.implementations.aws import (
                AWSCertificateRepository,
            )

            table_name = self.config.get("dynamodb_table", "apuntador-certificates")
            region = self.config.get("aws_region", "eu-west-1")
            auto_create = self.config.get("auto_create_resources", False)

            return AWSCertificateRepository(
                table_name=table_name,
                region_name=region,
                auto_create_table=auto_create,
            )

        elif self.provider == "azure":
            # TODO: Implement Azure CosmosDB repository
            raise NotImplementedError(AZURE_NOT_IMPLEMENTED_ERROR)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_secrets_repository(self) -> SecretsRepository:
        """
        Get secrets repository for configured provider.

        Returns:
            SecretsRepository implementation

        Raises:
            ValueError: If provider is not supported
        """
        if self.provider == "local":
            from apuntador.infrastructure.implementations.local import (
                LocalSecretsRepository,
            )

            base_dir = self.config.get("base_dir", "./.local_infrastructure/secrets")
            return LocalSecretsRepository(base_dir=base_dir)

        elif self.provider == "aws":
            from apuntador.infrastructure.implementations.aws import (
                AWSSecretsRepository,
            )

            region = self.config.get("aws_region", "eu-west-1")
            prefix = self.config.get("secrets_prefix", "apuntador")

            return AWSSecretsRepository(
                region_name=region,
                prefix=prefix,
            )

        elif self.provider == "azure":
            # TODO: Implement Azure Key Vault repository
            raise NotImplementedError(AZURE_NOT_IMPLEMENTED_ERROR)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_storage_repository(self) -> StorageRepository:
        """
        Get storage repository for configured provider.

        Returns:
            StorageRepository implementation

        Raises:
            ValueError: If provider is not supported
        """
        if self.provider == "local":
            from apuntador.infrastructure.implementations.local import (
                LocalStorageRepository,
            )

            base_dir = self.config.get("base_dir", "./.local_infrastructure/storage")
            return LocalStorageRepository(base_dir=base_dir)

        elif self.provider == "aws":
            from apuntador.infrastructure.implementations.aws import (
                AWSStorageRepository,
            )

            bucket_name = self.config.get("s3_bucket", "apuntador-certificates")
            region = self.config.get("aws_region", "eu-west-1")
            prefix = self.config.get("s3_prefix", "certificates")
            auto_create = self.config.get("auto_create_resources", False)

            return AWSStorageRepository(
                bucket_name=bucket_name,
                region_name=region,
                prefix=prefix,
                auto_create_bucket=auto_create,
            )

        elif self.provider == "azure":
            # TODO: Implement Azure Blob Storage repository
            raise NotImplementedError(AZURE_NOT_IMPLEMENTED_ERROR)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
