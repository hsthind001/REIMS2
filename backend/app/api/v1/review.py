"""
Review Workflow API

Endpoints for reviewing and correcting extracted financial data
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization
from app.models.organization import Organization
from app.services.review_service import ReviewService
from app.schemas.review import (
    ReviewQueueResponse,
    ApproveRecordRequest,
    ApproveRecordResponse,
    CorrectRecordRequest,
    CorrectRecordResponse,
    RecordDetailResponse
)


router = APIRouter()


@router.get("/review/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    document_type: Optional[str] = Query(None, description="Filter by document type (balance_sheet, income_statement, cash_flow, rent_roll)"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical (<85%), warning (85-95%), or all"),
    period_year: Optional[int] = Query(None, description="Filter by period year (e.g., 2025)"),
    period_month: Optional[int] = Query(None, ge=1, le=12, description="Filter by period month (1-12)"),
    skip: int = Query(0, ge=0, description="Number of records to skip (pagination)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get all items needing review across all financial tables
    
    Returns records with `needs_review = true` from:
    - balance_sheet_data
    - income_statement_data
    - cash_flow_data
    - rent_roll_data
    
    **Filters:**
    - property_code: Filter by specific property
    - document_type: Filter by financial statement type
    - severity: Filter by severity level (critical, warning, all)
    - period_year / period_month: Filter by specific fiscal period
    
    **Pagination:**
    - skip: Number of records to skip
    - limit: Maximum records to return (max 500)
    
    **Returns:**
    - List of review items with property/period context
    - Total count of items needing review
    - Pagination metadata
    """
    try:
        review_service = ReviewService(db, organization_id=current_org.id)
        result = review_service.get_review_queue(
            property_code=property_code,
            document_type=document_type,
            severity=severity,
            period_year=period_year,
            period_month=period_month,
            skip=skip,
            limit=limit
        )
        
        return ReviewQueueResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review queue: {str(e)}"
        )


@router.get("/review/{record_id}", response_model=RecordDetailResponse)
async def get_record_details(
    record_id: int = Path(..., description="Record ID"),
    table_name: str = Query(..., description="Table name (balance_sheet_data, income_statement_data, etc.)"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get detailed information about a specific record
    
    Returns complete record data including:
    - All financial fields
    - Property and period information
    - Review status
    - Extraction confidence
    
    **Parameters:**
    - record_id: ID of the record to retrieve
    - table_name: Which table to query (required query parameter)
    
    **Returns:**
    - Complete record details with all fields
    """
    try:
        review_service = ReviewService(db, organization_id=current_org.id)
        record = review_service.get_record_details(record_id, table_name)
        
        return RecordDetailResponse(**record)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get record details: {str(e)}"
        )


@router.put("/review/{record_id}/approve", response_model=ApproveRecordResponse)
async def approve_record(
    record_id: int = Path(..., description="Record ID to approve"),
    request: ApproveRecordRequest = ...,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Mark a record as reviewed and approved without changes
    
    Sets:
    - needs_review = false
    - reviewed = true
    - reviewed_by = current_user_id
    - reviewed_at = current timestamp
    - review_notes = optional notes
    
    Creates audit trail entry with action="approve"
    
    **Parameters:**
    - record_id: ID of the record to approve
    - table_name: Which table the record is in
    - notes: Optional approval notes
    
    **Returns:**
    - Success status
    - Review timestamp
    - Audit trail ID
    
    **Authentication Required**
    """
    try:
        review_service = ReviewService(db, organization_id=current_org.id)
        
        # Get user ID from current_user
        user_id = current_user.get("id", 1)  # Default to 1 if not available
        
        result = review_service.approve_record(
            record_id=record_id,
            table_name=request.table_name,
            user_id=user_id,
            notes=request.notes
        )
        
        return ApproveRecordResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve record: {str(e)}"
        )


@router.put("/review/{record_id}/correct", response_model=CorrectRecordResponse)
async def correct_record(
    record_id: int = Path(..., description="Record ID to correct"),
    request: CorrectRecordRequest = ...,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Correct field values in a record and mark as reviewed
    
    **Supports correcting ANY field:**
    - Numeric fields: amount, period_amount, ytd_amount, monthly_rent, unit_area_sqft, etc.
    - Text fields: account_name, tenant_name, unit_number, etc.
    
    **Automatic actions:**
    1. Updates specified fields with new values
    2. Marks record as reviewed (needs_review=false, reviewed=true)
    3. Creates audit trail entry with old_values and new_values
    4. Triggers smart metrics recalculation based on table:
       - balance_sheet_data → recalc balance sheet + ratios
       - income_statement_data → recalc income statement + margins + performance
       - cash_flow_data → recalc cash flow metrics
       - rent_roll_data → recalc occupancy + performance
    
    **Parameters:**
    - record_id: ID of the record to correct
    - table_name: Which table the record is in
    - corrections: Dict of field_name: new_value pairs
    - notes: Reason for correction
    - recalculate_metrics: Whether to trigger metrics recalc (default: true)
    
    **Returns:**
    - Success status
    - Changed fields list
    - Old and new values
    - Audit trail ID
    - Metrics recalculation result
    
    **Authentication Required**
    
    **Example Request:**
    ```json
    {
      "table_name": "balance_sheet_data",
      "corrections": {
        "amount": 52000.00,
        "account_name": "Cash - Operating Account"
      },
      "notes": "Corrected based on bank statement verification",
      "recalculate_metrics": true
    }
    ```
    """
    try:
        review_service = ReviewService(db, organization_id=current_org.id)
        
        # Get user ID from current_user
        user_id = current_user.get("id", 1)  # Default to 1 if not available
        
        result = review_service.correct_record(
            record_id=record_id,
            table_name=request.table_name,
            corrections=request.corrections,
            user_id=user_id,
            notes=request.notes,
            recalculate_metrics=request.recalculate_metrics
        )
        
        return CorrectRecordResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to correct record: {str(e)}"
        )


@router.post("/review/{record_id}/bulk-approve")
async def bulk_approve_records(
    record_ids: list[int],
    table_name: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Approve multiple records at once
    
    Useful for batch approval of verified records
    
    **Parameters:**
    - record_ids: List of record IDs to approve
    - table_name: Table containing the records
    - notes: Optional notes applied to all records
    
    **Returns:**
    - Summary of approvals (success count, failed count)
    
    **Authentication Required**
    """
    try:
        review_service = ReviewService(db)
        user_id = current_user.get("id", 1)
        
        results = {
            "total": len(record_ids),
            "approved": 0,
            "failed": 0,
            "errors": []
        }
        
        for record_id in record_ids:
            try:
                review_service.approve_record(
                    record_id=record_id,
                    table_name=table_name,
                    user_id=user_id,
                    notes=notes
                )
                results["approved"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "record_id": record_id,
                    "error": str(e)
                })
        
        return results
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk approve failed: {str(e)}"
        )
