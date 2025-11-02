"""
AWS DynamoDB implementation for certificate storage using PynamoDB ORM.

This module provides certificate metadata storage using AWS DynamoDB
for scalable, distributed certificate registry. Uses PynamoDB for
type-safe, Pythonic DynamoDB operations.
"""

from datetime import UTC, datetime, timedelta

try:
    from pynamodb.attributes import (
        BooleanAttribute,
        UnicodeAttribute,
        UTCDateTimeAttribute,
    )
    from pynamodb.indexes import AllProjection, GlobalSecondaryIndex
    from pynamodb.models import Model

    PYNAMODB_AVAILABLE = True
except ImportError:
    PYNAMODB_AVAILABLE = False

from apuntador.core.logging import logger
from apuntador.infrastructure.repositories.certificate_repository import (
    Certificate,
    CertificateRepository,
)


class SerialIndex(GlobalSecondaryIndex):
    """Global Secondary Index for serial number lookups."""

    class Meta:
        index_name = "SerialIndex"
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()

    # Index key
    serial_number = UnicodeAttribute(hash_key=True)


class ExpirationIndex(GlobalSecondaryIndex):
    """Global Secondary Index for expiration queries."""

    class Meta:
        index_name = "ExpirationIndex"
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()

    # Partition key for device_id, range key for expires_at
    device_id = UnicodeAttribute(hash_key=True)
    expires_at = UTCDateTimeAttribute(range_key=True)


class CertificateModel(Model):
    """PynamoDB model for certificate storage.

    DynamoDB Table Schema:
    - Partition Key: device_id (string)
    - Sort Key: serial_number (string)
    - Attributes: platform, issued_at, expires_at, certificate_pem, revoked,
                 revoked_at, revocation_reason

    Global Secondary Indexes:
    - SerialIndex: serial_number (partition key) for whitelist lookups
    - ExpirationIndex: device_id (partition) + expires_at (range) for expiring certs

    Note: table_name and region are configured dynamically in AWSCertificateRepository.__init__
    """

    class Meta:
        # These will be set dynamically from settings
        table_name = None  # Will be set from settings
        region = None  # Will be set from settings

    # Primary keys
    device_id = UnicodeAttribute(hash_key=True)
    serial_number = UnicodeAttribute(range_key=True)

    # Attributes
    platform = UnicodeAttribute()
    issued_at = UTCDateTimeAttribute()
    expires_at = UTCDateTimeAttribute()
    certificate_pem = UnicodeAttribute()
    revoked = BooleanAttribute(default=False)
    revoked_at = UTCDateTimeAttribute(null=True)
    revocation_reason = UnicodeAttribute(null=True)

    # Global Secondary Indexes
    serial_index = SerialIndex()
    expiration_index = ExpirationIndex()


class AWSCertificateRepository(CertificateRepository):
    """AWS DynamoDB implementation of CertificateRepository using PynamoDB.

    Uses PynamoDB ORM for type-safe, Pythonic DynamoDB operations.
    Provides automatic table creation, connection pooling, and retry logic.

    Environment Variables:
    - AWS_REGION: AWS region (default: us-east-1)
    - AWS_ACCESS_KEY_ID: AWS access key (optional if using IAM role)
    - AWS_SECRET_ACCESS_KEY: AWS secret key (optional if using IAM role)
    - DYNAMODB_TABLE_NAME: Table name (default: apuntador-certificates)
    """

    def __init__(
        self,
        table_name: str = "apuntador-certificates",
        region_name: str = "eu-west-1",
        auto_create_table: bool = False,
    ):
        """Initialize PynamoDB model.

        Args:
            table_name: DynamoDB table name (from settings.aws_dynamodb_table)
            region_name: AWS region (from settings.aws_region)
            auto_create_table: If True, create table if it doesn't exist
        """
        if not PYNAMODB_AVAILABLE:
            raise ImportError(
                "pynamodb is required for AWS implementations. "
                "Install with: uv add pynamodb"
            )

        # Validate inputs
        if not table_name:
            raise ValueError("table_name cannot be empty")
        if not region_name:
            raise ValueError("region_name cannot be empty")

        # Configure PynamoDB model dynamically
        CertificateModel.Meta.table_name = table_name
        CertificateModel.Meta.region = region_name

        self.table_name = table_name
        self.region_name = region_name

        if auto_create_table:
            self._ensure_table_exists()

        logger.info(
            f"Initialized AWSCertificateRepository (PynamoDB) with table={table_name}, region={region_name}"
        )

    def _ensure_table_exists(self) -> None:
        """Create DynamoDB table if it doesn't exist using PynamoDB."""
        try:
            # Check if table exists
            if not CertificateModel.exists():
                logger.info(f"Creating DynamoDB table: {self.table_name}")

                # Create table with indexes
                CertificateModel.create_table(
                    read_capacity_units=5,
                    write_capacity_units=5,
                    wait=True,  # Wait for table to be active
                )

                logger.info(f"Table {self.table_name} created successfully")
            else:
                logger.debug(f"Table {self.table_name} already exists")

        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise

    async def save_certificate(self, certificate: Certificate) -> None:
        """Save certificate metadata to DynamoDB.

        Args:
            certificate: Certificate object to save
        """
        try:
            cert_model = CertificateModel(
                device_id=certificate.device_id,
                serial_number=certificate.serial,
            )
            cert_model.platform = certificate.platform
            cert_model.issued_at = certificate.issued_at
            cert_model.expires_at = certificate.expires_at
            cert_model.certificate_pem = certificate.certificate_pem
            cert_model.revoked = certificate.revoked

            cert_model.save()

            logger.debug(
                f"Saved certificate: device={certificate.device_id}, serial={certificate.serial}"
            )

        except Exception as e:
            logger.error(f"Failed to save certificate: {e}")
            raise

    async def get_certificate(self, device_id: str) -> Certificate | None:
        """Get the latest certificate for a device.

        Args:
            device_id: Device identifier

        Returns:
            Certificate object or None if not found
        """
        try:
            # Query all certificates for device, get the first one (latest by serial)
            results = list(
                CertificateModel.query(
                    hash_key=device_id,
                    scan_index_forward=False,  # Descending order
                    limit=1,
                )
            )

            if not results:
                return None

            return self._model_to_certificate(results[0])

        except Exception as e:
            logger.error(f"Failed to get certificate for {device_id}: {e}")
            raise

    async def get_certificate_by_serial(self, serial: str) -> Certificate | None:
        """Get certificate by serial number.

        Args:
            serial: Certificate serial number

        Returns:
            Certificate object or None if not found
        """
        try:
            # Query SerialIndex
            results = list(
                CertificateModel.serial_index.query(
                    hash_key=serial,
                    limit=1,
                )
            )

            if not results:
                return None

            return self._model_to_certificate(results[0])

        except Exception as e:
            logger.error(f"Failed to get certificate by serial {serial}: {e}")
            raise

    async def is_serial_whitelisted(self, serial: str) -> bool:
        """Check if certificate serial is whitelisted.

        Args:
            serial: Certificate serial number

        Returns:
            True if whitelisted (exists and not revoked)
        """
        cert = await self.get_certificate_by_serial(serial)
        return cert is not None and not cert.revoked

    async def revoke_certificate(
        self, device_id: str, reason: str | None = None
    ) -> None:
        """Revoke a device's certificate.

        Args:
            device_id: Device identifier
            reason: Optional revocation reason
        """
        cert = await self.get_certificate(device_id)
        if not cert:
            logger.warning(f"Cannot revoke non-existent certificate for {device_id}")
            return

        try:
            # Get the certificate model
            cert_model = CertificateModel.get(hash_key=device_id, range_key=cert.serial)

            # Update revocation fields
            cert_model.revoked = True
            cert_model.revoked_at = datetime.now(UTC)
            cert_model.revocation_reason = reason or "Manual revocation"

            cert_model.save()

            logger.info(f"Revoked certificate: device={device_id}, reason={reason}")

        except Exception as e:
            logger.error(f"Failed to revoke certificate: {e}")
            raise

    async def list_expiring_certificates(self, days: int = 7) -> list[Certificate]:
        """List certificates expiring within specified days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of expiring certificates
        """
        expiration_threshold = datetime.now(UTC) + timedelta(days=days)

        try:
            certificates = []

            # Scan table for expiring certificates
            # Note: Scanning is not efficient for large tables
            # In production, consider maintaining a separate expiration queue
            for cert_model in CertificateModel.scan():
                if (
                    not cert_model.revoked
                    and cert_model.expires_at <= expiration_threshold
                ):
                    certificates.append(self._model_to_certificate(cert_model))

            logger.debug(
                f"Found {len(certificates)} certificates expiring within {days} days"
            )
            return certificates

        except Exception as e:
            logger.error(f"Failed to list expiring certificates: {e}")
            raise

    async def list_all_certificates(self) -> list[Certificate]:
        """
        List all stored certificates.

        Returns:
            List of all certificate metadata in the repository
        """
        try:
            certificates = [
                self._model_to_certificate(cert_model)
                for cert_model in CertificateModel.scan()
            ]

            logger.debug(f"Retrieved {len(certificates)} total certificates")
            return certificates

        except Exception as e:
            logger.error(f"Failed to list all certificates: {e}")
            raise

    def _model_to_certificate(self, model: CertificateModel) -> Certificate:
        """Convert PynamoDB model to Certificate object.

        Args:
            model: PynamoDB CertificateModel instance

        Returns:
            Certificate object
        """
        return Certificate(
            device_id=model.device_id,
            serial=model.serial_number,
            platform=model.platform,
            issued_at=model.issued_at,
            expires_at=model.expires_at,
            certificate_pem=model.certificate_pem,
            revoked=model.revoked,
        )
