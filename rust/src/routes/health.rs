use axum::{
    routing::get,
    Json, Router,
};
use serde_json::{json, Value};

async fn health() -> Json<Value> {
    Json(json!({
        "status": "healthy",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

pub fn routes() -> Router {
    Router::new().route("/health", get(health))
}
