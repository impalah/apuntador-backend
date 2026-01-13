use apuntador_backend::{config::Settings, core::logging, routes::create_router};
use lambda_http::{run, Error};
use std::sync::Arc;
use tower::ServiceBuilder;

#[tokio::main]
async fn main() -> Result<(), Error> {
    logging::init_tracing();
    
    let settings = Arc::new(Settings::from_env().expect("Failed to load settings"));
    
    let app = create_router(settings);
    
    let service = ServiceBuilder::new()
        .service(app);
    
    run(service).await
}
