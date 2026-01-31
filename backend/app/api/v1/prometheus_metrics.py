"""
Prometheus metrics endpoint (P1 Observability).
Exposes app-wide metrics for monitoring.
"""
from fastapi import APIRouter
from fastapi.responses import Response, PlainTextResponse

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus scrape endpoint. Returns metrics in text format."""
    try:
        from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST
        output = generate_latest(REGISTRY)
        return Response(content=output, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        return PlainTextResponse(content=f"# Error collecting metrics: {e}\n", status_code=500)
