"""
AWS Secrets Manager implementation for secrets storage.

This module provides secure secret storage using AWS Secrets Manager.
Secrets are encrypted at rest using AWS KMS.
"""


try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from apuntador.core.logging import logger
from apuntador.infrastructure.repositories.secrets_repository import (
    SecretsRepository,
)


class AWSSecretsRepository(SecretsRepository):
    """AWS Secrets Manager implementation of SecretsRepository.

    This implementation stores secrets in AWS Secrets Manager with:
    - Automatic encryption at rest using AWS KMS
    - Secret versioning support
    - Access control via IAM policies
    - Audit logging via CloudTrail

    Environment Variables:
    - AWS_REGION: AWS region (default: us-east-1)
    - AWS_ACCESS_KEY_ID: AWS access key (optional if using IAM role)
    - AWS_SECRET_ACCESS_KEY: AWS secret key (optional if using IAM role)
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        prefix: str = "apuntador",
    ):
        """Initialize AWS Secrets Manager client.

        Args:
            region_name: AWS region for Secrets Manager
            prefix: Prefix for all secret names (e.g., "apuntador/dev")
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for AWS implementations. "
                "Install with: pip install boto3"
            )

        self.region_name = region_name
        self.prefix = prefix
        self.client = boto3.client("secretsmanager", region_name=region_name)

        logger.info(
            f"Initialized AWSSecretsRepository with region={region_name}, prefix={prefix}"
        )

    def _get_secret_name(self, key: str) -> str:
        """Generate full secret name with prefix."""
        return f"{self.prefix}/{key}"

    async def store_secret(self, key: str, value: str) -> None:
        """Store a secret in AWS Secrets Manager.

        Args:
            key: Secret key (will be prefixed)
            value: Secret value (will be encrypted at rest)
        """
        secret_name = self._get_secret_name(key)

        try:
            # Try to create new secret
            self.client.create_secret(
                Name=secret_name,
                SecretString=value,
                Description=f"Apuntador secret: {key}",
            )
            logger.info(f"Created secret: {secret_name}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceExistsException":
                # Secret exists, update it
                self.client.put_secret_value(
                    SecretId=secret_name,
                    SecretString=value,
                )
                logger.info(f"Updated secret: {secret_name}")
            else:
                logger.error(f"Failed to store secret {secret_name}: {e}")
                raise

    async def get_secret(self, key: str) -> str | None:
        """Retrieve a secret from AWS Secrets Manager.

        Args:
            key: Secret key (will be prefixed)

        Returns:
            Secret value or None if not found
        """
        secret_name = self._get_secret_name(key)

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            logger.debug(f"Retrieved secret: {secret_name}")
            return response["SecretString"]

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.debug(f"Secret not found: {secret_name}")
                return None
            else:
                logger.error(f"Failed to get secret {secret_name}: {e}")
                raise

    async def delete_secret(self, key: str) -> None:
        """Delete a secret from AWS Secrets Manager.

        Note: Secrets are scheduled for deletion (7-30 days recovery window)
        rather than immediately deleted.

        Args:
            key: Secret key (will be prefixed)
        """
        secret_name = self._get_secret_name(key)

        try:
            # Schedule deletion with 7-day recovery window
            self.client.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=7,
            )
            logger.info(f"Scheduled secret deletion: {secret_name} (7-day recovery)")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.debug(f"Secret already deleted: {secret_name}")
            else:
                logger.error(f"Failed to delete secret {secret_name}: {e}")
                raise

    async def list_secrets(self) -> list[str]:
        """List all secrets with the configured prefix.

        Returns:
            List of secret keys (without prefix)
        """
        try:
            paginator = self.client.get_paginator("list_secrets")
            secret_keys = []

            for page in paginator.paginate():
                for secret in page["SecretList"]:
                    name = secret["Name"]
                    # Remove prefix if present
                    if name.startswith(f"{self.prefix}/"):
                        key = name[len(self.prefix) + 1 :]
                        secret_keys.append(key)

            logger.debug(
                f"Listed {len(secret_keys)} secrets with prefix: {self.prefix}"
            )
            return secret_keys

        except ClientError as e:
            logger.error(f"Failed to list secrets: {e}")
            raise

    async def get_ca_private_key(self) -> str:
        """
        Retrieve CA private key in PEM format.

        Returns:
            PEM-encoded CA private key

        Raises:
            Exception: If key not found or access denied
        """
        key = await self.get_secret("ca-private-key")
        if key is None:
            raise ValueError("CA private key not found in secrets storage")
        return key

    async def store_ca_private_key(self, private_key_pem: str) -> None:
        """
        Store CA private key securely.

        Args:
            private_key_pem: PEM-encoded CA private key

        Raises:
            Exception: If storage operation fails
        """
        await self.store_secret("ca-private-key", private_key_pem)
        logger.info("CA private key stored successfully")

    async def get_ca_certificate(self) -> str:
        """
        Retrieve CA certificate in PEM format.

        Returns:
            PEM-encoded CA certificate

        Raises:
            Exception: If certificate not found
        """
        cert = await self.get_secret("ca-certificate")
        if cert is None:
            raise ValueError("CA certificate not found in secrets storage")
        return cert

    async def store_ca_certificate(self, certificate_pem: str) -> None:
        """
        Store CA certificate.

        Args:
            certificate_pem: PEM-encoded CA certificate

        Raises:
            Exception: If storage operation fails
        """
        await self.store_secret("ca-certificate", certificate_pem)
        logger.info("CA certificate stored successfully")
