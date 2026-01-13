use axum::{
    routing::post,
    Router,
};
use std::sync::Arc;
use crate::config::Settings;

pub fn routes(_settings: Arc<Settings>) -> Router {
    Router::new()
        .route("/oauth/authorize/:provider", post(authorize))
}

async fn authorize() -> &'static str {
    "OAuth authorize - TODO"
}
