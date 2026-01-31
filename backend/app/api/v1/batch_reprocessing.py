"""
Batch Reprocessing API

REST endpoints for batch reprocessing of documents for anomaly detection.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization, require_org_role
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_property_for_org
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
    current_user: User = Depends(require_org_role("editor")),
    current_org: Organization = Depends(get_current_organization),
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
    if request.property_ids:
        for pid in request.property_ids:
            if not get_property_for_org(db, current_org.id, pid):
                raise HTTPException(status_code=404, detail=f"Property {pid} not found")
    try:
        service = BatchReprocessingService(db)
        from app.services.audit_service import log_action
        job = service.create_batch_job(
            user_id=current_user.id,
            property_ids=request.property_ids,
            organization_id=current_org.id,
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end,
            document_types=request.document_types,
            extraction_status_filter=request.extraction_status_filter,
            job_name=request.job_name
        )
        log_action(db, "batch_job.created", current_user.id, current_org.id, "batch_reprocessing_job", str(job.id), f"Created job {job.job_name or job.id} ({job.total_documents} docs)")
        
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


def _job_belongs_to_org(db, job_id: int, org_id: int) -> bool:
    """Verify batch job's properties belong to org. Returns True if accessible."""
    from app.models.batch_reprocessing_job import BatchReprocessingJob
    job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
    if not job:
        return False
    if not job.property_ids:
        return True  # Job has no property filter; legacy jobs - allow (initiated_by filters by user)
    return all(get_property_for_org(db, org_id, pid) for pid in job.property_ids)


@router.get("/jobs/{job_id}", response_model=BatchJobStatusResponse)
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get current status of a batch reprocessing job.
    
    Returns detailed progress information including:
    - Progress percentage
    - Processed/successful/failed counts
    - Estimated completion time
    - Results summary
    """
    if not _job_belongs_to_org(db, job_id, current_org.id):
        raise HTTPException(status_code=404, detail="Job not found")
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
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Cancel a running or queued batch job.
    
    Only jobs in 'queued' or 'running' status can be cancelled.
    Cancelled jobs cannot be restarted.
    """
    if not _job_belongs_to_org(db, job_id, current_org.id):
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        service = BatchReprocessingService(db)
        service.cancel_job(job_id)
        from app.services.audit_service import log_action
        log_action(db, "batch_job.cancelled", current_user.id, current_org.id, "batch_reprocessing_job", str(job_id), f"Cancelled job {job_id}")
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
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
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
        
        # Filter to jobs accessible by current org
        result = []
        for job in jobs:
            if not _job_belongs_to_org(db, job.id, current_org.id):
                continue
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
