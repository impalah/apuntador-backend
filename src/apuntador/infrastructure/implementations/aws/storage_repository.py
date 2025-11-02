"""
AWS S3 implementation for file storage.

This module provides file storage using AWS S3 with:
- Automatic encryption at rest (AES-256)
- Versioning support
- Access control via IAM policies
- CDN integration via CloudFront (optional)
"""


try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from apuntador.core.logging import logger
from apuntador.infrastructure.repositories.storage_repository import (
    StorageRepository,
)


class AWSStorageRepository(StorageRepository):
    """AWS S3 implementation of StorageRepository.

    This implementation stores files in S3 with:
    - Server-side encryption (SSE-S3 or SSE-KMS)
    - Optional versioning
    - Configurable bucket and prefix
    - Pre-signed URLs for temporary access

    Environment Variables:
    - AWS_REGION: AWS region (default: us-east-1)
    - AWS_ACCESS_KEY_ID: AWS access key (optional if using IAM role)
    - AWS_SECRET_ACCESS_KEY: AWS secret key (optional if using IAM role)
    - S3_BUCKET_NAME: S3 bucket name (default: apuntador-certificates)
    """

    def __init__(
        self,
        bucket_name: str = "apuntador-certificates",
        region_name: str = "us-east-1",
        prefix: str = "certificates",
        auto_create_bucket: bool = False,
    ):
        """Initialize S3 client.

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region
            prefix: Prefix for all S3 keys (like a folder)
            auto_create_bucket: If True, create bucket if it doesn't exist
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for AWS implementations. "
                "Install with: pip install boto3"
            )

        self.bucket_name = bucket_name
        self.region_name = region_name
        self.prefix = prefix
        self.client = boto3.client("s3", region_name=region_name)

        if auto_create_bucket:
            self._ensure_bucket_exists()

        logger.info(
            f"Initialized AWSStorageRepository with bucket={bucket_name}, "
            f"region={region_name}, prefix={prefix}"
        )

    def _ensure_bucket_exists(self) -> None:
        """Create S3 bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} already exists")
            return

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code != "404":
                raise

        # Bucket doesn't exist, create it
        logger.info(f"Creating S3 bucket: {self.bucket_name}")

        try:
            if self.region_name == "us-east-1":
                # us-east-1 doesn't require LocationConstraint
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": self.region_name},
                )

            # Enable server-side encryption
            self.client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                },
            )

            # Enable versioning (optional but recommended)
            self.client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={"Status": "Enabled"},
            )

            logger.info(f"Bucket {self.bucket_name} created successfully")

        except ClientError as e:
            logger.error(f"Failed to create bucket: {e}")
            raise

    def _get_s3_key(self, path: str) -> str:
        """Generate full S3 key with prefix."""
        # Remove leading slash if present
        path = path.lstrip("/")
        return f"{self.prefix}/{path}" if self.prefix else path

    async def upload_file(self, path: str, content: bytes) -> str:
        """Upload file to S3.

        Args:
            path: File path (will be prefixed)
            content: File content as bytes

        Returns:
            S3 URI (s3://bucket/key)
        """
        s3_key = self._get_s3_key(path)

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ServerSideEncryption="AES256",
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.debug(f"Uploaded file to S3: {s3_uri}")
            return s3_uri

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    async def download_file(self, path: str) -> bytes | None:
        """Download file from S3.

        Args:
            path: File path (will be prefixed)

        Returns:
            File content as bytes or None if not found
        """
        s3_key = self._get_s3_key(path)

        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            content = response["Body"].read()
            logger.debug(f"Downloaded file from S3: s3://{self.bucket_name}/{s3_key}")
            return content

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.debug(f"File not found in S3: {s3_key}")
                return None
            else:
                logger.error(f"Failed to download file from S3: {e}")
                raise

    async def delete_file(self, path: str) -> None:
        """Delete file from S3.

        Note: If versioning is enabled, this creates a delete marker
        rather than permanently deleting the file.

        Args:
            path: File path (will be prefixed)
        """
        s3_key = self._get_s3_key(path)

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            logger.info(f"Deleted file from S3: {s3_key}")

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise

    async def file_exists(self, path: str) -> bool:
        """Check if file exists in S3.

        Args:
            path: File path (will be prefixed)

        Returns:
            True if file exists
        """
        s3_key = self._get_s3_key(path)

        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error(f"Failed to check file existence: {e}")
                raise

    async def get_public_url(self, path: str, expiration: int = 3600) -> str | None:
        """Generate pre-signed URL for temporary public access.

        Args:
            path: File path (will be prefixed)
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Pre-signed URL or None if file doesn't exist
        """
        s3_key = self._get_s3_key(path)

        if not await self.file_exists(path):
            return None

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=expiration,
            )
            logger.debug(
                f"Generated pre-signed URL for {s3_key} (expires in {expiration}s)"
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            raise

    async def list_files(self, prefix: str = "") -> list[str]:
        """List all files with given prefix.

        Args:
            prefix: Additional prefix to filter files

        Returns:
            List of file paths (without bucket prefix)
        """
        s3_prefix = self._get_s3_key(prefix)

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            file_paths = []

            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=s3_prefix,
            ):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]
                    # Remove prefix to get relative path
                    if self.prefix and key.startswith(f"{self.prefix}/"):
                        relative_path = key[len(self.prefix) + 1 :]
                        file_paths.append(relative_path)
                    else:
                        file_paths.append(key)

            logger.debug(f"Listed {len(file_paths)} files with prefix: {s3_prefix}")
            return file_paths

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            raise
