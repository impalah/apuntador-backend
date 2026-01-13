use axum::{
    extract::Request,
    http::HeaderValue,
    middleware::Next,
    response::Response,
};
use uuid::Uuid;

pub const TRACE_ID_HEADER: &str = "x-trace-id";

pub async fn trace_id_middleware(mut req: Request, next: Next) -> Response {
    let trace_id = Uuid::new_v4().to_string();
    
    req.headers_mut().insert(
        TRACE_ID_HEADER,
        HeaderValue::from_str(&trace_id).unwrap(),
    );
    
    let mut response = next.run(req).await;
    
    response.headers_mut().insert(
        TRACE_ID_HEADER,
        HeaderValue::from_str(&trace_id).unwrap(),
    );
    
    response
}
