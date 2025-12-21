"""
Batch Reprocessing API Schemas

Pydantic models for batch reprocessing request/response.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime


class BatchJobCreate(BaseModel):
    """Request to create a batch reprocessing job."""
    property_ids: Optional[List[int]] = Field(None, description="List of property IDs to reprocess")
    date_range_start: Optional[date] = Field(None, description="Start date filter")
    date_range_end: Optional[date] = Field(None, description="End date filter")
    document_types: Optional[List[str]] = Field(None, description="Document types to reprocess (balance_sheet, income_statement, etc.)")
    extraction_status_filter: str = Field("all", description="Filter by extraction status: all, completed, failed")
    job_name: Optional[str] = Field(None, description="Optional human-readable job name")

    class Config:
        json_schema_extra = {
            "example": {
                "property_ids": [1, 2, 3],
                "date_range_start": "2024-01-01",
                "date_range_end": "2024-12-31",
                "document_types": ["balance_sheet", "income_statement"],
                "extraction_status_filter": "completed",
                "job_name": "Q4 2024 Anomaly Reprocessing"
            }
        }


class BatchJobResponse(BaseModel):
    """Response for batch job creation."""
    job_id: int
    job_name: Optional[str]
    status: str
    total_documents: int
    created_at: datetime
    task_id: Optional[str] = None

    class Config:
        from_attributes = True


class BatchJobStatusResponse(BaseModel):
    """Response for batch job status."""
    job_id: int
    job_name: Optional[str]
    status: str
    progress_pct: int
    total_documents: int
    processed_documents: int
    successful_count: int
    failed_count: int
    skipped_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion_at: Optional[datetime]
    celery_task_id: Optional[str]
    results_summary: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class BatchJobListItem(BaseModel):
    """Batch job list item."""
    id: int
    job_name: Optional[str]
    status: str
    total_documents: int
    processed_documents: int
    created_at: datetime
    initiated_by: Optional[int]

    class Config:
        from_attributes = True

