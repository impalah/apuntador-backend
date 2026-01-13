"""
PKCE (Proof Key for Code Exchange) utilities.
"""

import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 128) -> str:
    """
    Generates a random code verifier for PKCE.

    Args:
        length: Length of the code verifier (43-128 characters)

    Returns:
        Code verifier in base64url format
    """
    if not 43 <= length <= 128:
        raise ValueError("Length must be between 43 and 128")

    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode("utf-8")
    return code_verifier[:length].rstrip("=")


def generate_code_challenge(code_verifier: str) -> str:
    """
    Generates a code challenge from the code verifier using SHA256.

    Args:
        code_verifier: Generated code verifier

    Returns:
        Code challenge in base64url format
    """
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge_bytes = base64.urlsafe_b64encode(digest)
    return code_challenge_bytes.decode("utf-8").rstrip("=")


def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
    """
    Verifies that the code verifier corresponds to the code challenge.

    Args:
        code_verifier: Received code verifier
        code_challenge: Expected code challenge

    Returns:
        True if they match, False otherwise
    """
    expected_challenge = generate_code_challenge(code_verifier)
    return expected_challenge == code_challenge
