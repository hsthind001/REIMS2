"""
Forensic Reconciliation API Endpoints

Provides RESTful API for forensic financial document reconciliation across
Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.

Endpoints for:
- Session management
- Match finding and approval
- Discrepancy resolution
- Dashboard and health score
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.forensic_reconciliation_service import ForensicReconciliationService


router = APIRouter(prefix="/forensic-reconciliation", tags=["forensic-reconciliation"])


# ==================== PYDANTIC MODELS ====================

class ReconciliationSessionCreate(BaseModel):
    """Request model for creating a reconciliation session"""
    property_id: int
    period_id: int
    session_type: str = "full_reconciliation"  # full_reconciliation, cross_document, specific_match
    auditor_id: Optional[int] = None


class RunReconciliationRequest(BaseModel):
    """Request model for running reconciliation"""
    use_exact: bool = True
    use_fuzzy: bool = True
    use_calculated: bool = True
    use_inferred: bool = True
    use_rules: bool = True


class ApproveMatchRequest(BaseModel):
    """Request model for approving a match"""
    notes: Optional[str] = None


class RejectMatchRequest(BaseModel):
    """Request model for rejecting a match"""
    reason: str


class ResolveDiscrepancyRequest(BaseModel):
    """Request model for resolving a discrepancy"""
    resolution_notes: str
    new_value: Optional[float] = None


# ==================== SESSION ENDPOINTS ====================

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: ReconciliationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new forensic reconciliation session
    
    Validates that all necessary documents exist for the property/period
    and creates a new reconciliation session.
    """
    service = ForensicReconciliationService(db)
    
    session = service.start_reconciliation_session(
        property_id=request.property_id,
        period_id=request.period_id,
        session_type=request.session_type,
        auditor_id=request.auditor_id or current_user.id
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property, period, or required documents not found"
        )
    
    return {
        "id": session.id,
        "property_id": session.property_id,
        "period_id": session.period_id,
        "session_type": session.session_type,
        "status": session.status,
        "auditor_id": session.auditor_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "summary": session.summary
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int = Path(..., description="Session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific reconciliation session
    """
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession
    
    session = db.query(ForensicReconciliationSession).filter(
        ForensicReconciliationSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "id": session.id,
        "property_id": session.property_id,
        "period_id": session.period_id,
        "session_type": session.session_type,
        "status": session.status,
        "auditor_id": session.auditor_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "summary": session.summary,
        "notes": session.notes
    }


@router.post("/sessions/{session_id}/run")
async def run_reconciliation(
    session_id: int = Path(..., description="Session ID"),
    request: Optional[RunReconciliationRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute reconciliation for a session
    
    Runs all matching engines and finds matches across all document types.
    """
    service = ForensicReconciliationService(db)
    
    if request is None:
        request = RunReconciliationRequest()
    
    result = service.find_all_matches(
        session_id=session_id,
        use_exact=request.use_exact,
        use_fuzzy=request.use_fuzzy,
        use_calculated=request.use_calculated,
        use_inferred=request.use_inferred,
        use_rules=request.use_rules
    )
    
    if 'error' in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result['error']
        )
    
    return result


@router.get("/sessions/{session_id}/matches")
async def get_session_matches(
    session_id: int = Path(..., description="Session ID"),
    match_type: Optional[str] = Query(None, description="Filter by match type (exact, fuzzy, calculated, inferred)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, modified)"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence score"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all matches for a session
    
    Optionally filter by match type, status, or confidence score.
    """
    from app.models.forensic_match import ForensicMatch
    
    query = db.query(ForensicMatch).filter(
        ForensicMatch.session_id == session_id
    )
    
    if match_type:
        query = query.filter(ForensicMatch.match_type == match_type)
    
    if status_filter:
        query = query.filter(ForensicMatch.status == status_filter)
    
    if min_confidence is not None:
        query = query.filter(ForensicMatch.confidence_score >= min_confidence)
    
    matches = query.all()
    
    service = ForensicReconciliationService(db)
    
    return {
        "session_id": session_id,
        "total": len(matches),
        "matches": [service._match_to_dict(m) for m in matches]
    }


@router.get("/sessions/{session_id}/discrepancies")
async def get_session_discrepancies(
    session_id: int = Path(..., description="Session ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (open, investigating, resolved, accepted)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all discrepancies for a session
    
    Optionally filter by severity or status.
    """
    from app.models.forensic_discrepancy import ForensicDiscrepancy
    
    query = db.query(ForensicDiscrepancy).filter(
        ForensicDiscrepancy.session_id == session_id
    )
    
    if severity:
        query = query.filter(ForensicDiscrepancy.severity == severity)
    
    if status_filter:
        query = query.filter(ForensicDiscrepancy.status == status_filter)
    
    discrepancies = query.all()
    
    service = ForensicReconciliationService(db)
    
    return {
        "session_id": session_id,
        "total": len(discrepancies),
        "discrepancies": [service._discrepancy_to_dict(d) for d in discrepancies]
    }


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int = Path(..., description="Session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a reconciliation session as complete
    
    Finalizes the session and marks it as approved.
    """
    service = ForensicReconciliationService(db)
    
    success = service.complete_session(
        session_id=session_id,
        auditor_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "message": "Session completed successfully",
        "session_id": session_id
    }


# ==================== MATCH ENDPOINTS ====================

@router.post("/matches/{match_id}/approve")
async def approve_match(
    match_id: int = Path(..., description="Match ID"),
    request: Optional[ApproveMatchRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a match
    
    Auditor review workflow - approves a match with optional notes.
    """
    service = ForensicReconciliationService(db)
    
    success = service.approve_match(
        match_id=match_id,
        auditor_id=current_user.id,
        notes=request.notes if request else None
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )
    
    return {
        "message": "Match approved successfully",
        "match_id": match_id
    }


@router.post("/matches/{match_id}/reject")
async def reject_match(
    match_id: int = Path(..., description="Match ID"),
    request: RejectMatchRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a match
    
    Auditor review workflow - rejects a match with a reason.
    """
    service = ForensicReconciliationService(db)
    
    success = service.reject_match(
        match_id=match_id,
        auditor_id=current_user.id,
        reason=request.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )
    
    return {
        "message": "Match rejected successfully",
        "match_id": match_id
    }


# ==================== DISCREPANCY ENDPOINTS ====================

@router.post("/discrepancies/{discrepancy_id}/resolve")
async def resolve_discrepancy(
    discrepancy_id: int = Path(..., description="Discrepancy ID"),
    request: ResolveDiscrepancyRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve a discrepancy
    
    Allows auditor to resolve discrepancies with rationale and optional new value.
    """
    service = ForensicReconciliationService(db)
    
    new_value = None
    if request.new_value is not None:
        new_value = Decimal(str(request.new_value))
    
    success = service.resolve_discrepancy(
        discrepancy_id=discrepancy_id,
        auditor_id=current_user.id,
        resolution_notes=request.resolution_notes,
        new_value=new_value
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discrepancy {discrepancy_id} not found"
        )
    
    return {
        "message": "Discrepancy resolved successfully",
        "discrepancy_id": discrepancy_id
    }


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/{property_id}/{period_id}")
async def get_dashboard(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reconciliation dashboard data
    
    Returns summary statistics and match details for dashboard display.
    """
    service = ForensicReconciliationService(db)
    
    dashboard_data = service.get_reconciliation_dashboard(
        property_id=property_id,
        period_id=period_id
    )
    
    return dashboard_data


@router.get("/health-score/{property_id}/{period_id}")
async def get_health_score(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reconciliation health score
    
    Returns the health score (0-100) for a property/period reconciliation.
    """
    service = ForensicReconciliationService(db)
    
    # Get most recent session
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession
    
    session = db.query(ForensicReconciliationSession).filter(
        ForensicReconciliationSession.property_id == property_id,
        ForensicReconciliationSession.period_id == period_id
    ).order_by(ForensicReconciliationSession.started_at.desc()).first()
    
    if not session:
        return {
            "property_id": property_id,
            "period_id": period_id,
            "health_score": None,
            "message": "No reconciliation session found"
        }
    
    # Run validation to get health score
    validation_result = service.validate_matches(session.id)
    
    return {
        "property_id": property_id,
        "period_id": period_id,
        "session_id": session.id,
        "health_score": validation_result.get('health_score', 0.0),
        "total_matches": validation_result.get('total_matches', 0),
        "discrepancies": validation_result.get('discrepancies', 0)
    }


@router.post("/sessions/{session_id}/validate")
async def validate_session(
    session_id: int = Path(..., description="Session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate matches and calculate health score
    
    Runs validation rules and identifies discrepancies.
    """
    service = ForensicReconciliationService(db)
    
    result = service.validate_matches(session_id=session_id)
    
    if 'error' in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result['error']
        )
    
    return result

