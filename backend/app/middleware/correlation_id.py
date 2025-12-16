"""
Correlation ID Middleware

Adds correlation ID to all requests for distributed tracing.
"""
import uuid
from contextvars import ContextVar
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)

# Context variables for request context
user_id_var: ContextVar[int] = ContextVar('user_id', default=None)
query_id_var: ContextVar[int] = ContextVar('query_id', default=None)
conversation_id_var: ContextVar[str] = ContextVar('conversation_id', default=None)
property_id_var: ContextVar[int] = ContextVar('property_id', default=None)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to requests
    
    - Generates UUID if not present in headers
    - Adds correlation ID to response headers
    - Stores in contextvars for logging
    """
    
    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        """
        Initialize correlation ID middleware
        
        Args:
            app: ASGI application
            header_name: Header name for correlation ID
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add correlation ID
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response with correlation ID header
        """
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set in context variable for logging
        correlation_id_var.set(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id
        
        return response


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context
    
    Returns:
        Correlation ID string or None
    """
    try:
        return correlation_id_var.get()
    except LookupError:
        return None


def set_user_id(user_id: int):
    """Set user ID in context"""
    user_id_var.set(user_id)


def get_user_id() -> Optional[int]:
    """Get user ID from context"""
    try:
        return user_id_var.get()
    except LookupError:
        return None


def set_query_id(query_id: int):
    """Set query ID in context"""
    query_id_var.set(query_id)


def get_query_id() -> Optional[int]:
    """Get query ID from context"""
    try:
        return query_id_var.get()
    except LookupError:
        return None


def set_conversation_id(conversation_id: str):
    """Set conversation ID in context"""
    conversation_id_var.set(conversation_id)


def get_conversation_id() -> Optional[str]:
    """Get conversation ID from context"""
    try:
        return conversation_id_var.get()
    except LookupError:
        return None


def set_property_id(property_id: int):
    """Set property ID in context"""
    property_id_var.set(property_id)


def get_property_id() -> Optional[int]:
    """Get property ID from context"""
    try:
        return property_id_var.get()
    except LookupError:
        return None

