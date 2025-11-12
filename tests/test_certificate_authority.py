"""
Unit tests for Certificate Authority service.

Tests CSR signing, certificate verification, revocation, and lifecycle management.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID

from apuntador.infrastructure import InfrastructureFactory
from apuntador.services.certificate_authority import CertificateAuthority


@pytest.fixture
def test_infrastructure_dir(tmp_path: Path) -> Path:
    """Create temporary infrastructure directory."""
    infra_dir = tmp_path / ".test_infrastructure"
    infra_dir.mkdir()

    # Create secrets directory
    secrets_dir = infra_dir / "secrets"
    secrets_dir.mkdir(mode=0o700)

    # Create certificates directory
    certs_dir = infra_dir / "certificates"
    certs_dir.mkdir()

    return infra_dir


@pytest.fixture
def infrastructure_factory(test_infrastructure_dir: Path) -> InfrastructureFactory:
    """Create infrastructure factory with local provider."""
    # Pass the secrets directory directly to factory
    # LocalSecretsRepository expects base_dir to BE the secrets directory
    secrets_dir = test_infrastructure_dir / "secrets"
    return InfrastructureFactory(provider="local", base_dir=secrets_dir)


@pytest_asyncio.fixture
async def certificate_authority_with_ca(
    test_infrastructure_dir: Path, infrastructure_factory: InfrastructureFactory
) -> CertificateAuthority:
    """
    Create Certificate Authority with test CA.

    Generates a test CA private key and certificate in the test infrastructure.
    """
    # Generate CA private key
    ca_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,  # Smaller for faster tests
        backend=default_backend(),
    )

    # Generate CA certificate
    ca_subject = x509.Name(
        [
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "Test Apuntador"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "Test CA"),
        ]
    )

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC).replace(tzinfo=None))
        .not_valid_after(datetime.now(UTC).replace(tzinfo=None) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_private_key, hashes.SHA256(), default_backend())
    )

    # Save to secrets repository
    secrets_dir = test_infrastructure_dir / "secrets"

    ca_key_path = secrets_dir / "ca_private_key.pem"

    def _write_key():
        with open(ca_key_path, "wb") as f:
            f.write(
                ca_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        os.chmod(ca_key_path, 0o600)

    await asyncio.to_thread(_write_key)

    ca_cert_path = secrets_dir / "ca_certificate.pem"

    def _write_cert():
        with open(ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    await asyncio.to_thread(_write_cert)

    # Create Certificate Authority
    ca = CertificateAuthority(infrastructure_factory)

    return ca


def generate_test_csr(device_id: str = "test-device-123") -> tuple[str, any]:
    """
    Generate a test Certificate Signing Request.

    Returns:
        Tuple of (CSR PEM string, private key)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate CSR
    subject = x509.Name(
        [
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, device_id),
        ]
    )

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return csr_pem, private_key


@pytest.mark.asyncio
async def test_sign_csr_android(certificate_authority_with_ca: CertificateAuthority):
    """Test signing CSR for Android device."""
    ca = certificate_authority_with_ca
    device_id = "android-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android"
    )

    # Verify certificate fields
    assert certificate.device_id == device_id
    assert certificate.platform == "android"
    assert certificate.revoked is False
    assert len(certificate.serial) > 0

    # Verify validity period (Android: 30 days)
    validity_days = (certificate.expires_at - certificate.issued_at).days
    assert validity_days == 30

    # Verify certificate is PEM
    assert certificate.certificate_pem.startswith("-----BEGIN CERTIFICATE-----")
    assert certificate.certificate_pem.endswith("-----END CERTIFICATE-----\n")


@pytest.mark.asyncio
async def test_sign_csr_desktop(certificate_authority_with_ca: CertificateAuthority):
    """Test signing CSR for desktop device."""
    ca = certificate_authority_with_ca
    device_id = "desktop-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="desktop"
    )

    # Verify validity period (Desktop: 7 days)
    validity_days = (certificate.expires_at - certificate.issued_at).days
    assert validity_days == 7


@pytest.mark.asyncio
async def test_sign_csr_custom_validity(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test signing CSR with custom validity period."""
    ca = certificate_authority_with_ca
    device_id = "custom-validity-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign with custom validity
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android", validity_days=15
    )

    # Verify custom validity
    validity_days = (certificate.expires_at - certificate.issued_at).days
    assert validity_days == 15


@pytest.mark.asyncio
async def test_verify_certificate(certificate_authority_with_ca: CertificateAuthority):
    """Test certificate verification."""
    ca = certificate_authority_with_ca
    device_id = "verify-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android"
    )

    # Verify certificate
    is_valid = await ca.verify_certificate(certificate.certificate_pem)
    assert is_valid is True


@pytest.mark.asyncio
async def test_get_ca_certificate(certificate_authority_with_ca: CertificateAuthority):
    """Test getting CA certificate."""
    ca = certificate_authority_with_ca

    # Get CA certificate
    ca_cert_pem = await ca.get_ca_certificate_pem()

    # Verify it's PEM
    assert ca_cert_pem.startswith("-----BEGIN CERTIFICATE-----")
    assert ca_cert_pem.endswith("-----END CERTIFICATE-----\n")

    # Parse and verify it's a CA certificate
    ca_cert = x509.load_pem_x509_certificate(
        ca_cert_pem.encode("utf-8"), default_backend()
    )

    basic_constraints = ca_cert.extensions.get_extension_for_oid(
        ExtensionOID.BASIC_CONSTRAINTS
    )
    assert basic_constraints.value.ca is True


@pytest.mark.asyncio
async def test_revoke_certificate(certificate_authority_with_ca: CertificateAuthority):
    """Test certificate revocation."""
    ca = certificate_authority_with_ca
    device_id = "revoke-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android"
    )

    # Revoke certificate
    success = await ca.revoke_certificate(device_id)
    assert success is True

    # Verify it's revoked in repository
    cert_repo = ca.factory.get_certificate_repository()
    stored_cert = await cert_repo.get_certificate(device_id)
    assert stored_cert is not None
    assert stored_cert.revoked is True


@pytest.mark.asyncio
async def test_revoke_nonexistent_certificate(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test revoking certificate that doesn't exist."""
    ca = certificate_authority_with_ca

    # Try to revoke non-existent device
    success = await ca.revoke_certificate("nonexistent-device")
    assert success is False


@pytest.mark.asyncio
async def test_list_expiring_certificates(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test listing expiring certificates."""
    ca = certificate_authority_with_ca

    # Create certificate expiring in 5 days
    device_id_expiring = "expiring-device"
    csr_pem, _ = generate_test_csr(device_id_expiring)
    await ca.sign_csr(
        csr_pem=csr_pem,
        device_id=device_id_expiring,
        platform="desktop",
        validity_days=5,
    )

    # Create certificate expiring in 20 days
    device_id_valid = "valid-device"
    csr_pem2, _ = generate_test_csr(device_id_valid)
    await ca.sign_csr(
        csr_pem=csr_pem2,
        device_id=device_id_valid,
        platform="android",
        validity_days=20,
    )

    # List certificates expiring in 7 days
    expiring = await ca.list_expiring_certificates(days=7)

    # Only the 5-day certificate should be listed
    assert len(expiring) == 1
    assert expiring[0].device_id == device_id_expiring


@pytest.mark.asyncio
async def test_certificate_has_required_extensions(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test that signed certificate has required X.509v3 extensions."""
    ca = certificate_authority_with_ca
    device_id = "extensions-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android"
    )

    # Parse certificate
    cert = x509.load_pem_x509_certificate(
        certificate.certificate_pem.encode("utf-8"), default_backend()
    )

    # Verify BasicConstraints (CA=FALSE)
    basic_constraints = cert.extensions.get_extension_for_oid(
        ExtensionOID.BASIC_CONSTRAINTS
    )
    assert basic_constraints.value.ca is False

    # Verify KeyUsage
    key_usage = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
    assert key_usage.value.digital_signature is True
    assert key_usage.value.key_encipherment is True

    # Verify ExtendedKeyUsage (CLIENT_AUTH)
    extended_key_usage = cert.extensions.get_extension_for_oid(
        ExtensionOID.EXTENDED_KEY_USAGE
    )
    assert ExtendedKeyUsageOID.CLIENT_AUTH in extended_key_usage.value

    # Verify SubjectKeyIdentifier exists
    subject_key_id = cert.extensions.get_extension_for_oid(
        ExtensionOID.SUBJECT_KEY_IDENTIFIER
    )
    assert subject_key_id is not None

    # Verify AuthorityKeyIdentifier exists
    authority_key_id = cert.extensions.get_extension_for_oid(
        ExtensionOID.AUTHORITY_KEY_IDENTIFIER
    )
    assert authority_key_id is not None


@pytest.mark.asyncio
async def test_invalid_csr_format(certificate_authority_with_ca: CertificateAuthority):
    """Test that invalid CSR format raises ValueError."""
    ca = certificate_authority_with_ca

    # Invalid CSR (not PEM)
    with pytest.raises(ValueError, match="Invalid CSR format"):
        await ca.sign_csr(
            csr_pem="not a valid CSR", device_id="test-device", platform="android"
        )


@pytest.mark.asyncio
async def test_unique_serial_numbers(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test that each certificate gets a unique serial number."""
    ca = certificate_authority_with_ca

    # Sign multiple CSRs
    serials = set()
    for i in range(10):
        device_id = f"device-{i}"
        csr_pem, _ = generate_test_csr(device_id)
        certificate = await ca.sign_csr(
            csr_pem=csr_pem, device_id=device_id, platform="android"
        )
        serials.add(certificate.serial)

    # All serials should be unique
    assert len(serials) == 10


@pytest.mark.asyncio
async def test_certificate_storage_in_repository(
    certificate_authority_with_ca: CertificateAuthority,
):
    """Test that signed certificate is stored in repository."""
    ca = certificate_authority_with_ca
    device_id = "storage-test-device"
    csr_pem, _ = generate_test_csr(device_id)

    # Sign CSR
    certificate = await ca.sign_csr(
        csr_pem=csr_pem, device_id=device_id, platform="android"
    )

    # Retrieve from repository
    cert_repo = ca.factory.get_certificate_repository()
    stored_cert = await cert_repo.get_certificate(device_id)

    assert stored_cert is not None
    assert stored_cert.device_id == device_id
    assert stored_cert.serial == certificate.serial

    # Verify serial is in whitelist
    is_whitelisted = await cert_repo.is_serial_whitelisted(certificate.serial)
    assert is_whitelisted is True
