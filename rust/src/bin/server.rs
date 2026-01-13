use apuntador_backend::{config::Settings, core::logging, routes::create_router};
use std::sync::Arc;
use tracing::info;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    logging::init_tracing();
    
    let settings = Arc::new(Settings::from_env()?);
    
    info!("Starting server on {}:{}", settings.host, settings.port);
    
    let app = create_router(settings.clone());
    
    let listener = tokio::net::TcpListener::bind(format!("{}:{}", settings.host, settings.port))
        .await?;
    
    info!("Server listening on {}", listener.local_addr()?);
    
    axum::serve(listener, app).await?;
    
    Ok(())
}
