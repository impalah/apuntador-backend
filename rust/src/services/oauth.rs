use async_trait::async_trait;

#[async_trait]
pub trait OAuthService: Send + Sync {
    fn get_authorization_url(&self, code_challenge: &str, state: &str) -> String;
    async fn exchange_code_for_token(&self, code: &str, code_verifier: &str) -> anyhow::Result<serde_json::Value>;
}
