use serde::{Deserialize, Serialize};
use validator::Validate;

#[derive(Debug, Deserialize, Validate)]
pub struct AuthorizeRequest {
    #[validate(url)]
    pub redirect_uri: String,
    
    #[serde(default)]
    pub state: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct AuthorizeResponse {
    pub authorization_url: String,
    pub state: String,
}

#[derive(Debug, Serialize)]
pub struct TokenResponse {
    pub access_token: String,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub refresh_token: Option<String>,
    
    pub expires_in: u64,
    pub token_type: String,
}
