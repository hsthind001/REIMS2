"""
Base API Response Schemas

Standardized response structures for consistent API responses across all endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Generic, TypeVar, Dict
from datetime import datetime
from enum import Enum


# Generic type for paginated items
T = TypeVar('T')


class ResponseStatus(str, Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"  # For bulk operations with mixed results


class ErrorCode(str, Enum):
    """Standardized error codes"""
    # Authentication/Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Processing errors
    PROCESSING_FAILED = "PROCESSING_FAILED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    TIMEOUT = "TIMEOUT"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"


class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error (for validation)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class BaseResponse(BaseModel):
    """Base response structure for all API responses"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    message: Optional[str] = Field(None, description="Optional message for the response")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class SuccessResponse(BaseResponse):
    """Standard success response"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    data: Optional[Any] = Field(None, description="Response payload")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {"id": 123}
            }
        }


class ErrorResponse(BaseResponse):
    """Standard error response"""
    status: ResponseStatus = Field(default=ResponseStatus.ERROR)
    error: ErrorDetail = Field(..., description="Error details")

    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Request failed",
                "timestamp": "2024-01-15T10:30:00Z",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid property code format",
                    "field": "property_code",
                    "details": {"expected_format": "ABC001"}
                }
            }
        }


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=1000, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def from_query(cls, total: int, page: int, page_size: int) -> "PaginationMeta":
        """Create pagination meta from query parameters"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class PaginatedResponse(BaseResponse, Generic[T]):
    """Generic paginated response"""
    data: List[T] = Field(default_factory=list, description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": [{"id": 1}, {"id": 2}],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 50,
                    "total_pages": 2,
                    "has_next": True,
                    "has_previous": False
                }
            }
        }


class BulkOperationResult(BaseModel):
    """Result of a single item in bulk operation"""
    id: Optional[int] = Field(None, description="ID of the processed item")
    identifier: Optional[str] = Field(None, description="Alternative identifier")
    success: bool = Field(..., description="Whether this item was processed successfully")
    message: Optional[str] = Field(None, description="Result message")
    error: Optional[ErrorDetail] = Field(None, description="Error if failed")


class BulkOperationResponse(BaseResponse):
    """Response for bulk operations"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    total_submitted: int = Field(..., description="Total items submitted")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: List[BulkOperationResult] = Field(default_factory=list, description="Individual results")

    class Config:
        schema_extra = {
            "example": {
                "status": "partial",
                "message": "Bulk operation completed with some failures",
                "timestamp": "2024-01-15T10:30:00Z",
                "total_submitted": 10,
                "successful": 8,
                "failed": 2,
                "results": [
                    {"id": 1, "success": True, "message": "Processed"},
                    {"id": 2, "success": False, "error": {"code": "NOT_FOUND", "message": "Item not found"}}
                ]
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict, description="Status of dependent services")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "redis": "healthy",
                    "minio": "healthy"
                }
            }
        }


class DeleteResponse(BaseResponse):
    """Standard delete operation response"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    deleted_id: Optional[int] = Field(None, description="ID of deleted resource")
    deleted_count: Optional[int] = Field(None, description="Number of deleted items (for bulk)")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Resource deleted successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "deleted_id": 123
            }
        }


class CreatedResponse(BaseResponse):
    """Standard create operation response"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    id: int = Field(..., description="ID of created resource")
    data: Optional[Any] = Field(None, description="Created resource data")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Resource created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "id": 123,
                "data": {"id": 123, "name": "New Resource"}
            }
        }


class TaskResponse(BaseResponse):
    """Response for async task submission"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    task_id: str = Field(..., description="Async task ID for status tracking")
    task_status: str = Field(default="pending", description="Current task status")
    result_url: Optional[str] = Field(None, description="URL to fetch results when complete")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Task submitted successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "task_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "task_status": "pending",
                "result_url": "/api/v1/tasks/a1b2c3d4-5678-90ab-cdef-1234567890ab"
            }
        }
