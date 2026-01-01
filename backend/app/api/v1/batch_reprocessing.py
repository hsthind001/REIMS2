"""
Batch Reprocessing API

REST endpoints for batch reprocessing of documents for anomaly detection.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.batch_reprocessing_service import BatchReprocessingService
from app.schemas.batch_reprocessing import (
    BatchJobCreate,
    BatchJobResponse,
    BatchJobStatusResponse,
    BatchJobListItem
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch-reprocessing", tags=["batch-reprocessing"])


@router.post("/reprocess", response_model=BatchJobResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_job(
    request: BatchJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create and start a batch reprocessing job.
    
    Creates a new batch job and immediately starts processing asynchronously.
    Returns job ID and Celery task ID for tracking progress.
    
    **Filters:**
    - property_ids: Optional list of property IDs
    - date_range_start/end: Optional date range
    - document_types: Optional list of document types
    - extraction_status_filter: Filter by extraction status (all, completed, failed)
    
    **Returns:**
    - job_id: Batch job ID for status tracking
    - task_id: Celery task ID
    - total_documents: Number of documents to process
    """
    try:
        service = BatchReprocessingService(db)
        
        # Create batch job
        job = service.create_batch_job(
            user_id=current_user.id,
            property_ids=request.property_ids,
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end,
            document_types=request.document_types,
            extraction_status_filter=request.extraction_status_filter,
            job_name=request.job_name
        )
        
        # Start the job immediately
        job_info = service.start_batch_job(job.id)
        
        return BatchJobResponse(
            job_id=job.id,
            job_name=job.job_name,
            status=job.status,
            total_documents=job.total_documents,
            created_at=job.created_at,
            task_id=job_info.get("task_id")
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating batch job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=BatchJobStatusResponse)
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current status of a batch reprocessing job.
    
    Returns detailed progress information including:
    - Progress percentage
    - Processed/successful/failed counts
    - Estimated completion time
    - Results summary
    """
    try:
        service = BatchReprocessingService(db)
        status_info = service.get_job_status(job_id)
        
        return BatchJobStatusResponse(**status_info)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running or queued batch job.
    
    Only jobs in 'queued' or 'running' status can be cancelled.
    Cancelled jobs cannot be restarted.
    """
    try:
        service = BatchReprocessingService(db)
        service.cancel_job(job_id)
        
        return {"status": "cancelled", "job_id": job_id, "message": "Job cancelled successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/jobs", response_model=List[BatchJobListItem])
async def list_jobs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status (queued, running, completed, failed, cancelled)"),
    job_type: Optional[str] = Query(None, description="Filter by job type (anomaly_reprocessing, alert_backfill)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List batch reprocessing jobs with optional filters.
    
    Returns list of jobs ordered by creation date (newest first).
    Default limit is 50 jobs.
    """
    try:
        service = BatchReprocessingService(db)
        
        # Use current user's ID if not specified
        filter_user_id = user_id if user_id else (current_user.id if not current_user.is_superuser else None)
        
        jobs = service.list_jobs(
            user_id=filter_user_id,
            status=status_filter,
            job_type=job_type,
            limit=limit
        )
        
        # Convert jobs to list items with all required fields
        result = []
        for job in jobs:
            # Calculate progress percentage
            progress_pct = 0
            if job.total_documents > 0:
                progress_pct = int((job.processed_documents / job.total_documents) * 100)
            
            result.append(BatchJobListItem(
                id=job.id,
                job_name=job.job_name,
                status=job.status,
                total_documents=job.total_documents,
                processed_documents=job.processed_documents,
                successful_count=job.successful_count,
                failed_count=job.failed_count,
                skipped_count=job.skipped_count,
                progress_pct=progress_pct,
                started_at=job.started_at,
                completed_at=job.completed_at,
                estimated_completion_at=job.estimated_completion_at,
                celery_task_id=job.celery_task_id,
                results_summary=job.results_summary,
                created_at=job.created_at,
                initiated_by=job.initiated_by
            ))
        
        return result
    
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )
