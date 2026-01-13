use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("OAuth error: {0}")]
    OAuth(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Internal server error")]
    Internal,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    details: Option<String>,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_message) = match self {
            AppError::OAuth(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::Validation(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::Internal => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "Internal server error".to_string(),
            ),
        };

        let body = Json(ErrorResponse {
            error: error_message,
            details: None,
        });

        (status, body).into_response()
    }
}
