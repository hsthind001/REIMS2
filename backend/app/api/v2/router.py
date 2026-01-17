"""
API v2 Router

Aggregates all v2 endpoints and provides deprecation headers for v1 compatibility.
"""
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from typing import Callable
import warnings

from app.api.v2 import API_VERSION, DEPRECATION_DATE


class DeprecatedRoute(APIRoute):
    """
    Custom route class that adds deprecation headers to v1 responses.

    Headers added:
    - Deprecation: RFC 8594 deprecation date
    - Sunset: When the API will be removed
    - X-API-Version: Current version
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            response: Response = await original_route_handler(request)

            # Add deprecation headers
            response.headers["X-API-Version"] = API_VERSION
            response.headers["Deprecation"] = f"date=\"{DEPRECATION_DATE}\""
            response.headers["Sunset"] = DEPRECATION_DATE
            response.headers["Link"] = "</api/v2>; rel=\"successor-version\""

            return response

        return custom_route_handler


def create_deprecated_router(prefix: str = "", tags: list = None) -> APIRouter:
    """
    Create a router that automatically adds deprecation headers.

    Usage:
        router = create_deprecated_router(prefix="/old", tags=["deprecated"])

    Args:
        prefix: URL prefix for the router
        tags: OpenAPI tags

    Returns:
        APIRouter with deprecation handling
    """
    return APIRouter(
        prefix=prefix,
        tags=tags or [],
        route_class=DeprecatedRoute
    )


# Main v2 router
router = APIRouter(prefix="/api/v2")


# Health check for v2
@router.get("/health")
async def health_check():
    """V2 API health check with version info."""
    return {
        "status": "healthy",
        "api_version": API_VERSION,
        "v1_deprecation_date": DEPRECATION_DATE
    }


# Import and include v2-specific routers here as they are created
# Example:
# from app.api.v2 import documents as documents_v2
# router.include_router(documents_v2.router, tags=["documents"])
