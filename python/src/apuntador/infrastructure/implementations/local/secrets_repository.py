"""
Local file-based secrets repository implementation.

Stores secrets as individual files in a local directory:
    {base_dir}/
        secrets/
            ca_private_key.pem
            ca_certificate.pem
            {secret_key}.txt

WARNING: For development only. Not secure for production.
Production should use AWS Secrets Manager or similar.
"""

from pathlib import Path

from loguru import logger

from apuntador.infrastructure.repositories.secrets_repository import SecretsRepository


class LocalSecretsRepository(SecretsRepository):
    """
    File-based secrets storage for local development.

    WARNING: Files are stored unencrypted. Use only for local development.
    """

    def __init__(self, base_dir: str = "./.local_infrastructure/secrets"):
        """
        Initialize local secrets repository.

        Args:
            base_dir: Base directory for secrets storage
        """
        self.base_dir = Path(base_dir)
        self.secrets_dir = self.base_dir  # Use base_dir directly, not subdirectory

        # Create directory if it doesn't exist
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions (owner read/write only)
        try:
            self.secrets_dir.chmod(0o700)
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")

        logger.info(f"Initialized LocalSecretsRepository at {self.base_dir}")
        logger.warning(
            "LocalSecretsRepository stores secrets UNENCRYPTED - for development only!"
        )

    def _secret_path(self, key: str) -> Path:
        """Get path to secret file."""
        return self.secrets_dir / f"{key}.txt"

    async def get_ca_private_key(self) -> str:
        """Retrieve CA private key."""
        key_path = self.secrets_dir / "ca_private_key.pem"

        if not key_path.exists():
            raise FileNotFoundError(
                f"CA private key not found at {key_path}. "
                "Run CA setup script to generate."
            )

        return key_path.read_text()

    async def store_ca_private_key(self, private_key_pem: str) -> None:
        """Store CA private key."""
        key_path = self.secrets_dir / "ca_private_key.pem"
        key_path.write_text(private_key_pem)

        # Set restrictive permissions
        try:
            key_path.chmod(0o600)
        except Exception as e:
            logger.warning(f"Could not set file permissions: {e}")

        logger.info("Stored CA private key")

    async def get_ca_certificate(self) -> str:
        """Retrieve CA certificate."""
        cert_path = self.secrets_dir / "ca_certificate.pem"

        if not cert_path.exists():
            raise FileNotFoundError(
                f"CA certificate not found at {cert_path}. "
                "Run CA setup script to generate."
            )

        return cert_path.read_text()

    async def store_ca_certificate(self, certificate_pem: str) -> None:
        """Store CA certificate."""
        cert_path = self.secrets_dir / "ca_certificate.pem"
        cert_path.write_text(certificate_pem)

        logger.info("Stored CA certificate")

    async def get_secret(self, key: str) -> str | None:
        """Retrieve arbitrary secret."""
        secret_path = self._secret_path(key)

        if not secret_path.exists():
            return None

        return secret_path.read_text()

    async def store_secret(self, key: str, value: str) -> None:
        """Store arbitrary secret."""
        secret_path = self._secret_path(key)
        secret_path.write_text(value)

        # Set restrictive permissions
        try:
            secret_path.chmod(0o600)
        except Exception as e:
            logger.warning(f"Could not set file permissions: {e}")

        logger.info(f"Stored secret: {key}")
