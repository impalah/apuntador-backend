"""
Integration test for CA setup script.

Tests the setup-ca.sh script and verifies CA generation works correctly.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_ca_dir():
    """Create a temporary directory for CA generation."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestCASetupScript:
    """Tests for CA generation script."""

    def test_ca_script_local_mode(self, temp_ca_dir):
        """Test CA generation in local mode."""
        script_path = Path(__file__).parent.parent / "scripts" / "setup-ca.sh"

        # Run script in local mode
        result = subprocess.run(
            [str(script_path), "--local", "--output", temp_ca_dir],
            capture_output=True,
            text=True,
            input="yes\n",  # Auto-confirm if CA exists
            encoding="utf-8",
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify files were created
        ca_key = Path(temp_ca_dir) / "ca_private_key.pem"
        ca_cert = Path(temp_ca_dir) / "ca_certificate.pem"
        ca_config = Path(temp_ca_dir) / "ca_openssl.cnf"

        assert ca_key.exists(), "CA private key not created"
        assert ca_cert.exists(), "CA certificate not created"
        assert ca_config.exists(), "CA config not created"

        # Verify file permissions (private key should be 0600)
        key_perms = oct(ca_key.stat().st_mode)[-3:]
        assert (
            key_perms == "600"
        ), f"Private key permissions should be 0600, got {key_perms}"

        # Verify CA certificate is valid X.509
        verify_result = subprocess.run(
            ["openssl", "x509", "-in", str(ca_cert), "-noout", "-text"],
            capture_output=True,
            text=True,
        )

        assert verify_result.returncode == 0, "CA certificate is invalid"
        assert "Apuntador Certificate Authority" in verify_result.stdout
        assert "CA:TRUE" in verify_result.stdout

        # Verify private key matches certificate
        key_modulus = subprocess.check_output(
            ["openssl", "rsa", "-noout", "-modulus", "-in", str(ca_key)],
            stderr=subprocess.DEVNULL,
        )
        cert_modulus = subprocess.check_output(
            ["openssl", "x509", "-noout", "-modulus", "-in", str(ca_cert)],
            stderr=subprocess.DEVNULL,
        )

        assert key_modulus == cert_modulus, "CA key does not match certificate"

    def test_ca_script_help(self):
        """Test CA script help output."""
        script_path = Path(__file__).parent.parent / "scripts" / "setup-ca.sh"

        result = subprocess.run(
            [str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Certificate Authority (CA) Setup Script" in result.stdout
        assert "Usage:" in result.stdout

    @pytest.mark.asyncio
    async def test_ca_loading_via_repository(self, temp_ca_dir):
        """Test loading CA through infrastructure repository."""
        from apuntador.infrastructure import InfrastructureFactory

        # Generate CA
        script_path = Path(__file__).parent.parent / "scripts" / "setup-ca.sh"
        subprocess.run(
            [str(script_path), "--local", "--output", temp_ca_dir],
            capture_output=True,
            input=b"yes\n",  # Use bytes, not string
        )

        # Load via repository
        factory = InfrastructureFactory(provider="local", base_dir=temp_ca_dir)
        secrets_repo = factory.get_secrets_repository()

        ca_key = await secrets_repo.get_ca_private_key()
        ca_cert = await secrets_repo.get_ca_certificate()

        assert ca_key.startswith("-----BEGIN")
        assert ca_cert.startswith("-----BEGIN CERTIFICATE-----")
        assert len(ca_key) > 1000  # RSA 4096 key should be large
        assert len(ca_cert) > 1000  # Certificate with extensions
