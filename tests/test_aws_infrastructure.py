"""
Unit tests for AWS infrastructure implementations.

Tests use mocking (pytest-mock) to avoid requiring actual AWS credentials.
For integration tests with localstack, see tests/integration/test_aws_localstack.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Mock boto3 before importing AWS implementations
pytest.importorskip("boto3", reason="boto3 required for AWS tests")


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for testing."""
    with patch("boto3.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_boto3_resource():
    """Mock boto3 resource for testing."""
    with patch("boto3.resource") as mock_resource:
        yield mock_resource


# ===========================
# AWS Secrets Manager Tests
# ===========================


class TestAWSSecretsRepository:
    """Tests for AWS Secrets Manager implementation."""

    @pytest.mark.asyncio
    async def test_store_secret_create_new(self, mock_boto3_client):
        """Test storing a new secret."""
        from apuntador.infrastructure.implementations.aws import AWSSecretsRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        repo = AWSSecretsRepository(region_name="us-east-1", prefix="test")

        await repo.store_secret("ca-private-key", "-----BEGIN PRIVATE KEY-----")

        # Should call create_secret
        mock_client_instance.create_secret.assert_called_once()
        call_args = mock_client_instance.create_secret.call_args
        assert call_args[1]["Name"] == "test/ca-private-key"
        assert call_args[1]["SecretString"] == "-----BEGIN PRIVATE KEY-----"

    @pytest.mark.asyncio
    async def test_store_secret_update_existing(self, mock_boto3_client):
        """Test updating an existing secret."""
        from botocore.exceptions import ClientError

        from apuntador.infrastructure.implementations.aws import AWSSecretsRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        # Simulate ResourceExistsException on create
        error_response = {"Error": {"Code": "ResourceExistsException"}}
        mock_client_instance.create_secret.side_effect = ClientError(
            error_response, "CreateSecret"
        )

        repo = AWSSecretsRepository(region_name="us-east-1", prefix="test")

        await repo.store_secret("ca-private-key", "-----BEGIN PRIVATE KEY-----")

        # Should call put_secret_value after create fails
        mock_client_instance.put_secret_value.assert_called_once()
        call_args = mock_client_instance.put_secret_value.call_args
        assert call_args[1]["SecretId"] == "test/ca-private-key"

    @pytest.mark.asyncio
    async def test_get_secret_exists(self, mock_boto3_client):
        """Test retrieving an existing secret."""
        from apuntador.infrastructure.implementations.aws import AWSSecretsRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        mock_client_instance.get_secret_value.return_value = {
            "SecretString": "secret-value"
        }

        repo = AWSSecretsRepository(region_name="us-east-1", prefix="test")

        value = await repo.get_secret("ca-private-key")

        assert value == "secret-value"
        mock_client_instance.get_secret_value.assert_called_once_with(
            SecretId="test/ca-private-key"
        )

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self, mock_boto3_client):
        """Test retrieving a non-existent secret."""
        from botocore.exceptions import ClientError

        from apuntador.infrastructure.implementations.aws import AWSSecretsRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_client_instance.get_secret_value.side_effect = ClientError(
            error_response, "GetSecretValue"
        )

        repo = AWSSecretsRepository(region_name="us-east-1", prefix="test")

        value = await repo.get_secret("nonexistent")

        assert value is None


# ===========================
# AWS DynamoDB Tests (PynamoDB)
# ===========================


class TestAWSCertificateRepository:
    """Tests for AWS DynamoDB implementation using PynamoDB."""

    @pytest.mark.asyncio
    async def test_save_certificate(self, mocker):
        """Test saving certificate to DynamoDB with PynamoDB."""
        from apuntador.infrastructure.implementations.aws import (
            AWSCertificateRepository,
        )
        from apuntador.infrastructure.repositories.certificate_repository import (
            Certificate,
        )

        # Mock PynamoDB Model.save() method
        mock_save = mocker.patch(
            "apuntador.infrastructure.implementations.aws.certificate_repository.CertificateModel.save"
        )

        repo = AWSCertificateRepository(
            table_name="test-table",
            region_name="us-east-1",
            auto_create_table=False,
        )

        cert = Certificate(
            device_id="device-123",
            serial="ABC123",
            platform="android",
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            certificate_pem="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            revoked=False,
        )

        await repo.save_certificate(cert)

        # Should call save() once
        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_certificate_by_serial(self, mocker):
        """Test retrieving certificate by serial number with PynamoDB."""
        from apuntador.infrastructure.implementations.aws import (
            AWSCertificateRepository,
        )
        from apuntador.infrastructure.implementations.aws.certificate_repository import (
            CertificateModel,
        )

        # Mock PynamoDB Model instance
        now = datetime.now(UTC)
        mock_cert_model = CertificateModel()
        mock_cert_model.device_id = "device-123"
        mock_cert_model.serial_number = "ABC123"
        mock_cert_model.platform = "android"
        mock_cert_model.issued_at = now
        mock_cert_model.expires_at = now + timedelta(days=30)
        mock_cert_model.certificate_pem = (
            "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
        )
        mock_cert_model.revoked = False

        # Mock the query on SerialIndex
        mock_query = mocker.patch.object(
            CertificateModel.serial_index,
            "query",
            return_value=iter([mock_cert_model]),
        )

        repo = AWSCertificateRepository(
            table_name="test-table",
            region_name="us-east-1",
            auto_create_table=False,
        )

        cert = await repo.get_certificate_by_serial("ABC123")

        assert cert is not None
        assert cert.device_id == "device-123"
        assert cert.serial == "ABC123"
        assert cert.platform == "android"
        mock_query.assert_called_once()


# ===========================
# AWS S3 Tests
# ===========================


class TestAWSStorageRepository:
    """Tests for AWS S3 implementation."""

    @pytest.mark.asyncio
    async def test_upload_file(self, mock_boto3_client):
        """Test uploading file to S3."""
        from apuntador.infrastructure.implementations.aws import AWSStorageRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        repo = AWSStorageRepository(
            bucket_name="test-bucket",
            region_name="us-east-1",
            prefix="certs",
            auto_create_bucket=False,
        )

        content = b"certificate-content"
        s3_uri = await repo.upload_file("device-123.pem", content)

        assert s3_uri == "s3://test-bucket/certs/device-123.pem"

        # Should call put_object
        mock_client_instance.put_object.assert_called_once()
        call_args = mock_client_instance.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "certs/device-123.pem"
        assert call_args[1]["Body"] == content

    @pytest.mark.asyncio
    async def test_download_file(self, mock_boto3_client):
        """Test downloading file from S3."""
        from apuntador.infrastructure.implementations.aws import AWSStorageRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        # Mock S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = b"certificate-content"
        mock_client_instance.get_object.return_value = {"Body": mock_body}

        repo = AWSStorageRepository(
            bucket_name="test-bucket",
            region_name="us-east-1",
            prefix="certs",
            auto_create_bucket=False,
        )

        content = await repo.download_file("device-123.pem")

        assert content == b"certificate-content"
        mock_client_instance.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="certs/device-123.pem",
        )

    @pytest.mark.asyncio
    async def test_file_exists(self, mock_boto3_client):
        """Test checking if file exists in S3."""
        from apuntador.infrastructure.implementations.aws import AWSStorageRepository

        mock_client_instance = MagicMock()
        mock_boto3_client.return_value = mock_client_instance

        # head_object succeeds = file exists
        mock_client_instance.head_object.return_value = {}

        repo = AWSStorageRepository(
            bucket_name="test-bucket",
            region_name="us-east-1",
            prefix="certs",
            auto_create_bucket=False,
        )

        exists = await repo.file_exists("device-123.pem")

        assert exists is True
        mock_client_instance.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="certs/device-123.pem",
        )


# ===========================
# Integration Tests
# ===========================


class TestInfrastructureFactoryAWS:
    """Test infrastructure factory with AWS provider."""

    def test_factory_creates_aws_repositories(
        self, mock_boto3_client, mock_boto3_resource
    ):
        """Test that factory creates AWS repository instances."""
        from apuntador.infrastructure import InfrastructureFactory

        factory = InfrastructureFactory(
            provider="aws",
            aws_region="us-west-2",
            dynamodb_table="test-certs",
            s3_bucket="test-bucket",
            secrets_prefix="test-app",
        )

        # Should create AWS repositories (with mocked boto3)
        cert_repo = factory.get_certificate_repository()
        assert cert_repo is not None

        secrets_repo = factory.get_secrets_repository()
        assert secrets_repo is not None

        storage_repo = factory.get_storage_repository()
        assert storage_repo is not None
