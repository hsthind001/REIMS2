"""
Workflow Locks API Endpoints

Handles workflow lock management, approval workflows, and operation checks
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from app.db.database import get_db
from app.services.workflow_lock_service import WorkflowLockService
from app.models.workflow_lock import WorkflowLock, LockReason, LockScope, LockStatus
from app.models.property import Property

router = APIRouter(prefix="/workflow-locks", tags=["workflow_locks"])
logger = logging.getLogger(__name__)


class CreateLockRequest(BaseModel):
    property_id: int
    lock_reason: str
    lock_scope: str
    title: str
    description: str
    locked_by: int
    alert_id: Optional[int] = None
    approval_committee: Optional[str] = None
    br_id: Optional[str] = None


class ReleaseLockRequest(BaseModel):
    unlocked_by: int
    resolution_notes: Optional[str] = None


class ApproveLockRequest(BaseModel):
    approved_by: int
    resolution_notes: str


class RejectLockRequest(BaseModel):
    rejected_by: int
    rejection_reason: str


class CheckOperationRequest(BaseModel):
    property_id: int
    operation: str  # "financial_update", "report_generation", "data_entry", "transaction"


@router.post("/create")
def create_lock(
    request: CreateLockRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new workflow lock

    Lock Reasons: DSCR_BREACH, OCCUPANCY_THRESHOLD, COVENANT_VIOLATION,
                  COMMITTEE_REVIEW, FINANCIAL_ANOMALY, VARIANCE_BREACH,
                  MANUAL_HOLD, DATA_QUALITY_ISSUE

    Lock Scopes: PROPERTY_ALL, FINANCIAL_UPDATES, REPORTING_ONLY,
                 TRANSACTION_APPROVAL, DATA_ENTRY
    """
    service = WorkflowLockService(db)

    try:
        result = service.create_lock(
            property_id=request.property_id,
            lock_reason=LockReason[request.lock_reason],
            lock_scope=LockScope[request.lock_scope],
            title=request.title,
            description=request.description,
            locked_by=request.locked_by,
            alert_id=request.alert_id,
            approval_committee=request.approval_committee,
            br_id=request.br_id,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create workflow lock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{lock_id}/release")
def release_lock(
    lock_id: int,
    request: ReleaseLockRequest,
    db: Session = Depends(get_db)
):
    """
    Release/unlock a workflow lock
    """
    service = WorkflowLockService(db)

    try:
        result = service.release_lock(
            lock_id=lock_id,
            unlocked_by=request.unlocked_by,
            resolution_notes=request.resolution_notes
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Failed to release workflow lock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{lock_id}/approve")
def approve_lock(
    lock_id: int,
    request: ApproveLockRequest,
    db: Session = Depends(get_db)
):
    """
    Approve a workflow lock (committee approval)
    """
    service = WorkflowLockService(db)

    try:
        result = service.approve_lock(
            lock_id=lock_id,
            approved_by=request.approved_by,
            resolution_notes=request.resolution_notes
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Failed to approve workflow lock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{lock_id}/reject")
def reject_lock(
    lock_id: int,
    request: RejectLockRequest,
    db: Session = Depends(get_db)
):
    """
    Reject a workflow lock (committee rejection)
    """
    service = WorkflowLockService(db)

    try:
        result = service.reject_lock(
            lock_id=lock_id,
            rejected_by=request.rejected_by,
            rejection_reason=request.rejection_reason
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Failed to reject workflow lock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-operation")
def check_operation_allowed(
    request: CheckOperationRequest,
    db: Session = Depends(get_db)
):
    """
    Check if an operation is allowed on a property

    Operations:
    - financial_update: Update financial data
    - report_generation: Generate reports
    - data_entry: Enter new data
    - transaction: Execute transactions

    Returns whether operation is allowed and any blocking locks
    """
    service = WorkflowLockService(db)

    try:
        result = service.check_operation_allowed(
            property_id=request.property_id,
            operation=request.operation
        )

        return {
            "success": True,
            "property_id": request.property_id,
            "operation": request.operation,
            **result
        }

    except Exception as e:
        logger.error(f"Failed to check operation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}")
def get_property_locks(
    property_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all workflow locks for a property
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = WorkflowLockService(db)

    try:
        lock_status = LockStatus[status] if status else None
        locks = service.get_property_locks(property_id, lock_status)

        return {
            "success": True,
            "property_id": property_id,
            "property_name": property.property_name,
            "locks": locks,
            "total": len(locks)
        }

    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        logger.error(f"Failed to get property locks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-approvals")
def get_pending_approvals(
    committee: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all locks pending committee approval

    Committees:
    - Finance Sub-Committee
    - Occupancy Sub-Committee
    - Risk Committee
    - Executive Committee
    """
    service = WorkflowLockService(db)

    try:
        locks = service.get_pending_approvals(committee)

        return {
            "success": True,
            "committee": committee or "All",
            "locks": locks,
            "total": len(locks)
        }

    except Exception as e:
        logger.error(f"Failed to get pending approvals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lock_id}")
def get_lock(
    lock_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific workflow lock by ID
    """
    lock = db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
    if not lock:
        raise HTTPException(status_code=404, detail="Workflow lock not found")

    # Get property details
    property = db.query(Property).filter(Property.id == lock.property_id).first()

    result = lock.to_dict()
    if property:
        result["property"] = {
            "id": property.id,
            "name": property.property_name,
            "code": property.property_code,
            "address": property.address,
        }

    return result


@router.get("/statistics/summary")
def get_lock_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about workflow locks across all properties
    """
    service = WorkflowLockService(db)

    try:
        stats = service.get_lock_statistics()

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Failed to get lock statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/properties/{property_id}/pause")
def pause_property_operations(
    property_id: int,
    reason: str,
    locked_by: int,
    db: Session = Depends(get_db)
):
    """
    Convenience endpoint to pause all operations on a property
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = WorkflowLockService(db)

    try:
        result = service.pause_property_operations(
            property_id=property_id,
            reason=reason,
            locked_by=locked_by
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Failed to pause property operations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/properties/{property_id}/resume")
def resume_property_operations(
    property_id: int,
    unlocked_by: int,
    resolution_notes: str,
    db: Session = Depends(get_db)
):
    """
    Convenience endpoint to resume all operations on a property
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = WorkflowLockService(db)

    try:
        result = service.resume_property_operations(
            property_id=property_id,
            unlocked_by=unlocked_by,
            resolution_notes=resolution_notes
        )

        return result

    except Exception as e:
        logger.error(f"Failed to resume property operations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
