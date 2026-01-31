"""
OpenTelemetry tracing (P1 Observability).
Optional: enable via ENABLE_OTEL_TRACING=true and OTEL_EXPORTER_OTLP_ENDPOINT.
"""
import logging
import os

logger = logging.getLogger(__name__)


def setup_otel_tracing(app) -> bool:
    """
    Instrument FastAPI app with OpenTelemetry tracing.
    Returns True if tracing was enabled, False otherwise.
    """
    if os.getenv("ENABLE_OTEL_TRACING", "").lower() not in ("true", "1", "yes"):
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        exporter_type = os.getenv("OTEL_TRACES_EXPORTER", "otlp")
        if exporter_type == "none":
            return False

        resource = Resource.create({
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "reims-backend"),
        })
        provider = TracerProvider(resource=resource)

        if exporter_type == "otlp":
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
            if not endpoint:
                logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set, skipping OTLP export")
                return False
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter()  # Uses OTEL_EXPORTER_OTLP_* env vars
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp-proto-http not installed, skipping tracing")
                return False
        else:
            return False

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        excluded = os.getenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "/health,/metrics,/api/v1/health")
        FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded)
        logger.info("OpenTelemetry tracing enabled")
        return True
    except Exception as e:
        logger.warning(f"OpenTelemetry setup failed: {e}")
        return False
