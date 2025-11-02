"""
Tests para utilidades PKCE.
"""

from apuntador.utils.pkce import (
    generate_code_challenge,
    generate_code_verifier,
    verify_code_challenge,
)


def test_generate_code_verifier():
    """Test generación de code verifier."""
    verifier = generate_code_verifier()
    assert len(verifier) == 128
    assert verifier.replace("-", "").replace("_", "").isalnum()


def test_generate_code_challenge():
    """Test generación de code challenge."""
    verifier = "test_verifier_1234567890"
    challenge = generate_code_challenge(verifier)
    assert len(challenge) > 0
    assert challenge.replace("-", "").replace("_", "").isalnum()


def test_verify_code_challenge():
    """Test verificación de code challenge."""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    assert verify_code_challenge(verifier, challenge) is True
    assert verify_code_challenge("wrong_verifier", challenge) is False
