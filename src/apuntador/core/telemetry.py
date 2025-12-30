"""
OpenTelemetry configuration for distributed tracing and metrics.

This module configures OpenTelemetry with:
- FastAPI automatic instrumentation
- HTTPX client instrumentation
- AWS X-Ray propagation for CloudWatch integration
- Custom trace ID integration with loguru
- AWS CloudWatch exporter via X-Ray
"""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from apuntador.config import settings

logger = logging.getLogger(__name__)


def configure_opentelemetry(
    service_name: str = "apuntador-backend",
    service_version: str | None = None,
    environment: str | None = None,
) -> None:
    """
    Configures OpenTelemetry with AWS X-Ray integration for CloudWatch.

    This function:
    1. Creates a resource with service information
    2. Configures TracerProvider with AWS X-Ray ID generator
    3. Sets up span exporters (Console for dev, OTLP for production)
    4. Configures AWS X-Ray propagator for distributed tracing
    5. Instruments FastAPI and HTTPX automatically

    Args:
        service_name: Name of the service (default: "apuntador-backend")
        service_version: Version of the service (default: from settings)
        environment: Environment name (default: from settings or "development")

    Example:
        >>> # In main.py
        >>> from apuntador.core.telemetry import configure_opentelemetry
        >>> configure_opentelemetry(
        ...     service_name="apuntador-backend",
        ...     service_version="1.0.0",
        ...     environment="production"
        ... )
    """
    # Default values from settings
    if service_version is None:
        service_version = getattr(settings, "version", "unknown")

    if environment is None:
        environment = getattr(settings, "environment", "development")

    # Create resource with service information
    resource = Resource.create(
        attributes={
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
            "cloud.provider": "aws",
            "cloud.platform": "aws_lambda",  # or "aws_ecs" depending on deployment
        }
    )

    # Configure TracerProvider with AWS X-Ray ID generator
    # This generates trace IDs compatible with AWS X-Ray format
    tracer_provider = TracerProvider(
        resource=resource,
        id_generator=AwsXRayIdGenerator(),  # AWS X-Ray compatible IDs
    )

    # Register tracer provider globally
    trace.set_tracer_provider(tracer_provider)

    # Configure span exporters
    _configure_span_exporters(tracer_provider, environment)

    # Configure AWS X-Ray propagator for distributed tracing
    # This ensures trace context is properly propagated across services
    set_global_textmap(AwsXRayPropagator())

    logger.info(
        f"✅ OpenTelemetry configured: service={service_name}, "
        f"version={service_version}, environment={environment}"
    )


def _configure_span_exporters(
    tracer_provider: TracerProvider,
    environment: str,
) -> None:
    """
    Configures span exporters based on environment.

    Args:
        tracer_provider: The tracer provider to add exporters to
        environment: Current environment name
    """
    # Development: Console exporter for debugging
    if environment in ["development", "dev", "local"]:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("📊 Console span exporter configured (development mode)")

    # Production: OTLP exporter to AWS X-Ray via ADOT Collector
    else:
        # AWS Distro for OpenTelemetry (ADOT) Collector endpoint
        # When running in AWS Lambda/ECS, the ADOT Collector is typically
        # at localhost:4317
        otlp_endpoint = getattr(
            settings, "otel_exporter_otlp_endpoint", "http://localhost:4317"
        )

        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use TLS in production if endpoint uses HTTPS
        )

        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"📊 OTLP span exporter configured: endpoint={otlp_endpoint}")


def instrument_fastapi(app) -> None:
    """
    Instruments a FastAPI application with OpenTelemetry.

    This adds automatic tracing for:
    - HTTP requests/responses
    - Request/response headers
    - Status codes and errors
    - Request duration

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from apuntador.core.telemetry import instrument_fastapi
        >>>
        >>> app = FastAPI()
        >>> instrument_fastapi(app)
    """
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls="/health,/metrics",  # Don't trace health checks
    )
    logger.info("✅ FastAPI instrumented with OpenTelemetry")


def instrument_httpx() -> None:
    """
    Instruments HTTPX client with OpenTelemetry.

    This adds automatic tracing for:
    - Outgoing HTTP requests
    - Request/response headers
    - HTTP method, URL, status code
    - Request duration

    Call this once at application startup.

    Example:
        >>> from apuntador.core.telemetry import instrument_httpx
        >>> instrument_httpx()
    """
    HTTPXClientInstrumentor().instrument()
    logger.info("✅ HTTPX client instrumented with OpenTelemetry")


def instrument_logging() -> None:
    """
    Instruments Python logging with OpenTelemetry.

    This automatically adds trace context (trace_id, span_id) to log records,
    enabling correlation between logs and traces in CloudWatch/X-Ray.

    Call this once at application startup, BEFORE configuring loguru.

    Example:
        >>> from apuntador.core.telemetry import instrument_logging
        >>> instrument_logging()
    """
    LoggingInstrumentor().instrument(set_logging_format=False)
    logger.info("✅ Logging instrumented with OpenTelemetry")


def get_current_trace_id() -> str:
    """
    Gets the current trace ID from OpenTelemetry context.

    This can be used to add trace_id to logs, responses, or custom metrics.

    Returns:
        Current trace ID in AWS X-Ray format, or "N/A" if no active trace

    Example:
        >>> from apuntador.core.telemetry import get_current_trace_id
        >>> trace_id = get_current_trace_id()
        >>> logger.info(f"Processing request", trace_id=trace_id)
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        trace_id = format(span.get_span_context().trace_id, "032x")
        return trace_id
    return "N/A"


def get_current_span_id() -> str:
    """
    Gets the current span ID from OpenTelemetry context.

    Returns:
        Current span ID, or "N/A" if no active span

    Example:
        >>> from apuntador.core.telemetry import get_current_span_id
        >>> span_id = get_current_span_id()
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        span_id = format(span.get_span_context().span_id, "016x")
        return span_id
    return "N/A"


# Example: Custom span creation
def create_span_example():
    """
    Example of creating custom spans for specific operations.

    Use this pattern when you want to trace specific functions or operations
    that aren't automatically instrumented.
    """
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("custom-operation") as span:
        # Add custom attributes to the span
        span.set_attribute("user.id", "12345")
        span.set_attribute("operation.type", "data-processing")

        # Your code here
        # ...

        # Add events to the span
        span.add_event("processing-started")

        # If an error occurs, record it
        try:
            # risky_operation()
            pass
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


__all__ = [
    "configure_opentelemetry",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_logging",
    "get_current_trace_id",
    "get_current_span_id",
]
