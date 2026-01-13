use serde::Deserialize;

#[derive(Debug, Deserialize, Clone)]
pub struct Settings {
    // Server
    pub host: String,
    pub port: u16,
    pub debug: bool,
    pub secret_key: String,
    
    // CORS
    pub allowed_origins: Vec<String>,
    
    // Google Drive OAuth
    pub google_client_id: String,
    pub google_client_secret: String,
    pub google_redirect_uri: String,
    
    // Dropbox OAuth
    pub dropbox_client_id: String,
    pub dropbox_client_secret: String,
    pub dropbox_redirect_uri: String,
}

impl Settings {
    pub fn from_env() -> Result<Self, config::ConfigError> {
        dotenvy::dotenv().ok();
        
        config::Config::builder()
            .add_source(config::Environment::default().separator("__"))
            .build()?
            .try_deserialize()
    }
}
