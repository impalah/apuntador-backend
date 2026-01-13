"""
Infrastructure abstraction layer for cloud-agnostic operations.

This module provides repository interfaces and implementations for:
- Certificate storage and management
- Secret storage (CA private key)
- File storage (truststore, CRLs)

Supports multiple providers via factory pattern:
- local: File-based storage for development
- aws: DynamoDB, S3, Secrets Manager
- azure: (future) CosmosDB, Blob Storage, Key Vault
"""

from apuntador.infrastructure.factory import InfrastructureFactory

__all__ = ["InfrastructureFactory"]
