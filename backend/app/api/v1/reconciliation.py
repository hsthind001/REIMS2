"""
Reconciliation API Endpoints

Provides RESTful API for reconciliation operations including:
- Starting reconciliation sessions
- Comparing PDF to database
- Resolving differences
- Generating reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

from app.api.dependencies import get_current_user, get_current_organization, get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.property import Property
from app.services.reconciliation_service import ReconciliationService


router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


# Pydantic models for request/response
class ReconciliationSessionCreate(BaseModel):
    property_code: str
    period_year: int
    period_month: int
    document_type: str


class ResolveDifferenceRequest(BaseModel):
    action: str  # accept_pdf, accept_db, manual_entry, ignore
    new_value: Optional[float] = None
    reason: str


class BulkResolveRequest(BaseModel):
    difference_ids: List[int]
    action: str  # accept_pdf, accept_db, ignore


# Endpoints
@router.post("/session")
async def create_reconciliation_session(
    request: ReconciliationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Start a new reconciliation session
    
    Creates a session to track reconciliation of PDF vs database data
    for a specific property, period, and document type.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    session = service.start_reconciliation_session(
        property_code=request.property_code,
        period_year=request.period_year,
        period_month=request.period_month,
        document_type=request.document_type,
        user_id=current_user.id
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Property or period not found")
    
    return {
        "session_id": session.id,
        "property_id": session.property_id,
        "period_id": session.period_id,
        "document_type": session.document_type,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None
    }


@router.get("/compare")
async def compare_pdf_to_database(
    property_code: str = Query(..., description="Property code"),
    year: int = Query(..., description="Period year"),
    month: int = Query(..., description="Period month"),
    doc_type: str = Query(..., description="Document type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Compare PDF extraction with database records
    
    Performs field-by-field comparison and returns differences with
    color-coded match statuses.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    result = service.compare_pdf_to_database(
        property_code=property_code,
        period_year=year,
        period_month=month,
        document_type=doc_type,
        user_id=current_user.id
    )
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


@router.get("/pdf-url")
async def get_pdf_url(
    property_code: str = Query(..., description="Property code"),
    year: int = Query(..., description="Period year"),
    month: int = Query(..., description="Period month"),
    doc_type: str = Query(..., description="Document type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get MinIO presigned URL for PDF viewing
    
    Returns a temporary URL (1 hour expiry) to view the PDF document.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    url = service.get_pdf_url(
        property_code=property_code,
        period_year=year,
        period_month=month,
        document_type=doc_type
    )
    
    if not url:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return {"pdf_url": url}


@router.post("/resolve/{difference_id}")
async def resolve_difference(
    difference_id: int,
    request: ResolveDifferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Resolve a single difference
    
    Applies correction and creates audit trail.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    new_value = Decimal(str(request.new_value)) if request.new_value is not None else None
    
    success = service.resolve_difference(
        difference_id=difference_id,
        action=request.action,
        new_value=new_value,
        reason=request.reason,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Difference not found")
    
    return {"success": True, "message": "Difference resolved successfully"}


@router.post("/bulk-resolve")
async def bulk_resolve_differences(
    request: BulkResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Bulk resolve multiple differences
    
    Applies same action to multiple differences in a transaction.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    result = service.bulk_resolve_differences(
        difference_ids=request.difference_ids,
        action=request.action,
        user_id=current_user.id
    )
    
    return result


@router.get("/sessions")
async def list_reconciliation_sessions(
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    limit: int = Query(50, description="Maximum number of sessions to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    List reconciliation sessions
    
    Returns recent reconciliation sessions with summary statistics.
    """
    service = ReconciliationService(db, organization_id=current_org.id)
    
    sessions = service.get_sessions(
        property_code=property_code,
        limit=limit
    )
    
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get details of a specific reconciliation session
    
    Returns session information and associated differences.
    """
    from app.models.reconciliation_session import ReconciliationSession
    from app.models.reconciliation_difference import ReconciliationDifference
    
    session = db.query(ReconciliationSession).join(
        Property, ReconciliationSession.property_id == Property.id
    ).filter(
        ReconciliationSession.id == session_id,
        Property.organization_id == current_org.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get differences
    differences = db.query(ReconciliationDifference).filter(
        ReconciliationDifference.session_id == session_id
    ).all()
    
    return {
        "session": {
            "id": session.id,
            "property_code": session.property.property_code,
            "property_name": session.property.property_name,
            "period_year": session.period.period_year,
            "period_month": session.period.period_month,
            "document_type": session.document_type,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "summary": session.summary
        },
        "differences": [
            {
                "id": d.id,
                "account_code": d.account_code,
                "account_name": d.account_name,
                "pdf_value": float(d.pdf_value) if d.pdf_value else None,
                "db_value": float(d.db_value) if d.db_value else None,
                "difference": float(d.difference) if d.difference else None,
                "difference_percent": float(d.difference_percent) if d.difference_percent else None,
                "difference_type": d.difference_type,
                "status": d.status,
                "needs_review": d.needs_review
            }
            for d in differences
        ]
    }


@router.put("/sessions/{session_id}/complete")
async def complete_reconciliation_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark reconciliation session as complete
    
    Finalizes the session and locks the reconciliation.
    """
    service = ReconciliationService(db)
    
    success = service.complete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session completed successfully"}


@router.get("/report/{session_id}")
async def generate_reconciliation_report(
    session_id: int,
    format: str = Query("excel", description="Report format: excel or pdf"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate reconciliation report
    
    Creates Excel or PDF report with summary and detailed differences.
    
    Note: This is a placeholder. Full implementation requires openpyxl/reportlab.
    """
    from app.models.reconciliation_session import ReconciliationSession
    from app.models.reconciliation_difference import ReconciliationDifference
    
    session = db.query(ReconciliationSession).filter(
        ReconciliationSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get differences
    differences = db.query(ReconciliationDifference).filter(
        ReconciliationDifference.session_id == session_id
    ).all()
    
    if format == "excel":
        # Generate Excel report
        # This would use openpyxl to create a workbook
        # For now, return CSV-like data
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Account Code', 'Account Name', 'PDF Value', 'DB Value',
            'Difference', 'Difference %', 'Type', 'Status'
        ])
        
        # Data rows
        for d in differences:
            writer.writerow([
                d.account_code,
                d.account_name,
                d.pdf_value,
                d.db_value,
                d.difference,
                d.difference_percent,
                d.difference_type,
                d.status
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=reconciliation_{session_id}.csv"
            }
        )
    
    elif format == "pdf":
        # Generate PDF report
        # This would use reportlab
        raise HTTPException(status_code=501, detail="PDF format not yet implemented")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
