// Main library root
pub mod config;
pub mod core;
pub mod error;
pub mod middleware;
pub mod models;
pub mod routes;
pub mod services;
pub mod utils;

// Re-exports for convenience
pub use error::AppError;
