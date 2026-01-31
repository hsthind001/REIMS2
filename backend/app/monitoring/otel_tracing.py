"""
OpenTelemetry tracing (P1 Observability).
Optional: enable via ENABLE_OTEL_TRACING=true and OTEL_EXPORTER_OTLP_ENDPOINT.
Instruments FastAPI, SQLAlchemy. Celery workers use worker_process_init.
"""
import logging
import os

logger = logging.getLogger(__name__)


def _create_otel_provider():
    """Create and set TracerProvider. Returns provider or None if disabled."""
    if os.getenv("ENABLE_OTEL_TRACING", "").lower() not in ("true", "1", "yes"):
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        exporter_type = os.getenv("OTEL_TRACES_EXPORTER", "otlp")
        if exporter_type == "none":
            return None
        if exporter_type == "otlp":
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
            if not endpoint:
                return None
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter()
            except ImportError:
                return None
        else:
            return None

        resource = Resource.create({
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "reims-backend"),
        })
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        return provider
    except Exception as e:
        logger.warning(f"OTel provider setup failed: {e}")
        return None


def setup_otel_tracing(app) -> bool:
    """
    Instrument FastAPI app, SQLAlchemy with OpenTelemetry tracing.
    Returns True if tracing was enabled, False otherwise.
    Celery workers instrument via worker_process_init in celery_config.
    """
    provider = _create_otel_provider()
    if not provider:
        return False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.db.database import engine

        excluded = os.getenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "/health,/metrics,/api/v1/health")
        FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded)
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("OpenTelemetry tracing enabled (FastAPI, SQLAlchemy)")
        return True
    except Exception as e:
        logger.warning(f"OpenTelemetry setup failed: {e}")
        return False


def setup_otel_celery() -> bool:
    """
    Set up OTel provider + instrument Celery. Call from worker_process_init.
    Worker must initialize tracing after process start (BatchSpanProcessor needs it).
    """
    provider = _create_otel_provider()
    if not provider:
        return False
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.db.database import engine

        CeleryInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("OpenTelemetry Celery + SQLAlchemy instrumentation enabled")
        return True
    except Exception as e:
        logger.warning(f"OpenTelemetry Celery setup failed: {e}")
        return False
