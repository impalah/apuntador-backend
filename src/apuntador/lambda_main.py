"""AWS Lambda handler using Mangum adapter."""

from mangum import Mangum

from apuntador.app_setup import add_root_endpoint, setup_app
from apuntador.application import create_app
from apuntador.core.logging import intercept_standard_logging

# Intercept logs from uvicorn and other libraries
intercept_standard_logging()

# Create FastAPI application using factory
app = create_app()

# Setup middleware and configuration
setup_app(app)

# Add root endpoint
add_root_endpoint(app)

# Configure as lambda handler
lambda_handler = Mangum(app)
