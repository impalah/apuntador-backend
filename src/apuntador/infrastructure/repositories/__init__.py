"""Abstract repository interfaces for infrastructure operations."""

from apuntador.infrastructure.repositories.certificate_repository import (
    Certificate,
    CertificateRepository,
)
from apuntador.infrastructure.repositories.secrets_repository import SecretsRepository
from apuntador.infrastructure.repositories.storage_repository import StorageRepository

__all__ = [
    "Certificate",
    "CertificateRepository",
    "SecretsRepository",
    "StorageRepository",
]
