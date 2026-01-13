pub mod health;
pub mod oauth;

use axum::{
    middleware,
    Router,
};
use std::sync::Arc;
use crate::config::Settings;
use crate::middleware::trace_id::trace_id_middleware;

pub fn create_router(settings: Arc<Settings>) -> Router {
    Router::new()
        .merge(health::routes())
        .merge(oauth::routes(settings))
        .layer(middleware::from_fn(trace_id_middleware))
}
