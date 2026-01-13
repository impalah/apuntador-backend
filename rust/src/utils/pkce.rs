use base64::{engine::general_purpose, Engine as _};
use rand::Rng;
use sha2::{Digest, Sha256};

/// Generate a cryptographically secure code verifier (43-128 chars)
pub fn generate_code_verifier(length: usize) -> String {
    let mut rng = rand::thread_rng();
    let random_bytes: Vec<u8> = (0..length).map(|_| rng.gen()).collect();
    general_purpose::URL_SAFE_NO_PAD.encode(&random_bytes)
}

/// Generate code challenge from verifier (SHA256 hash, base64url encoded)
pub fn generate_code_challenge(code_verifier: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(code_verifier.as_bytes());
    let hash = hasher.finalize();
    general_purpose::URL_SAFE_NO_PAD.encode(&hash)
}

/// Verify that code_challenge matches code_verifier
pub fn verify_code_challenge(code_verifier: &str, code_challenge: &str) -> bool {
    generate_code_challenge(code_verifier) == code_challenge
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_code_verifier() {
        let verifier = generate_code_verifier(128);
        assert!(!verifier.is_empty());
        assert!(verifier.len() >= 43);
    }

    #[test]
    fn test_generate_code_challenge() {
        let verifier = "test_verifier_123456789";
        let challenge = generate_code_challenge(verifier);
        assert!(!challenge.is_empty());
    }

    #[test]
    fn test_verify_code_challenge() {
        let verifier = generate_code_verifier(64);
        let challenge = generate_code_challenge(&verifier);
        assert!(verify_code_challenge(&verifier, &challenge));
        assert!(!verify_code_challenge(&verifier, "wrong_challenge"));
    }
}
