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
import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.api.dependencies import get_current_user, get_current_organization, get_db
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import (
    get_property_for_org,
    get_period_for_org,
    get_forensic_reconciliation_session_for_org,
    get_forensic_match_for_org,
    get_forensic_discrepancy_for_org,
)
from app.services.forensic_reconciliation_service import ForensicReconciliationService
from app.services.materiality_service import MaterialityService
from app.services.exception_tiering_service import ExceptionTieringService
from app.services.chart_of_accounts_service import ChartOfAccountsService
from app.services.calculated_rules_engine import CalculatedRulesEngine
from app.services.health_score_service import HealthScoreService
from app.models.materiality_config import MaterialityConfig, AccountRiskClass
from app.models.auto_resolution_rule import AutoResolutionRule
from app.models.account_synonym import AccountSynonym
from app.models.account_mapping import AccountMapping
from app.models.calculated_rule import CalculatedRule
from app.models.health_score_config import HealthScoreConfig
from app.models.property import Property


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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Create a new forensic reconciliation session. Tenant-scoped.
    """
    if not get_property_for_org(db, current_org.id, request.property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, request.period_id):
        raise HTTPException(status_code=404, detail="Period not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get details of a specific reconciliation session. Tenant-scoped."""
    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Execute reconciliation for a session. Tenant-scoped."""
    import logging
    logger = logging.getLogger(__name__)
    service = ForensicReconciliationService(db)
    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    if request is None:
        request = RunReconciliationRequest()
    
    try:
        result = service.find_all_matches(
            session_id=session_id,
            use_exact=request.use_exact,
            use_fuzzy=request.use_fuzzy,
            use_calculated=request.use_calculated,
            use_inferred=request.use_inferred,
            use_rules=request.use_rules
        )
        
        # Commit matches to database (even if tiering had errors)
        # Matches are flushed but not committed by the service
        try:
            db.commit()
            logger.info(f"Committed matches for session {session_id}")
        except Exception as commit_error:
            logger.error(f"Error committing matches: {commit_error}")
            db.rollback()
            # Don't fail - matches might still be in database from tiering commits
        
        # Check for errors but don't fail if we have partial results
        if 'error' in result:
            # If we have matches stored, return them with error info
            if result.get('summary', {}).get('total_matches', 0) > 0:
                result['warning'] = result.pop('error')
                logger.warning(f"Reconciliation completed with warnings: {result['warning']}")
            else:
                # No matches found, return error
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result['error']
                )
        
        # Add diagnostic information if no matches found
        if result.get('summary', {}).get('total_matches', 0) == 0:
            # Get diagnostics from diagnostics service
            try:
                diagnostics = service.get_diagnostics(session.property_id, session.period_id)
                result['diagnostic'] = {
                    'message': 'No matches found. This may indicate:',
                    'possible_reasons': [
                        'No financial data extracted for this property/period',
                        'Documents uploaded but not yet processed/extracted',
                        'Account codes do not match expected patterns',
                        'Data exists but no cross-document relationships found'
                    ],
                    'suggestion': 'Check that documents have been uploaded and extracted for this property and period',
                    'data_availability': diagnostics.get('data_availability', {}),
                    'missing_accounts': diagnostics.get('missing_accounts', {}),
                    'recommendations': diagnostics.get('recommendations', [])
                }
            except Exception as diag_error:
                logger.warning(f"Failed to get diagnostics: {diag_error}")
                result['diagnostic'] = {
                    'message': 'No matches found',
                    'suggestion': 'Check that documents have been uploaded and extracted'
                }
        else:
            # Matches found - add success diagnostic
            result['diagnostic'] = {
                'message': f"Successfully found {result.get('summary', {}).get('total_matches', 0)} matches",
                'matches_stored': result.get('summary', {}).get('total_matches', 0)
            }
            # Include failure info if available
            if 'diagnostic' in result and 'matches_failed' in result['diagnostic']:
                result['diagnostic']['matches_failed'] = result['diagnostic'].get('matches_failed', 0)
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error during reconciliation: {e}", exc_info=True)
        # Try to return partial results if session exists
        try:
            # Check if any matches were stored before the error
            from app.models.forensic_match import ForensicMatch
            stored_count = db.query(ForensicMatch).filter(
                ForensicMatch.session_id == session_id
            ).count()
            
            if stored_count > 0:
                # Return partial success
                return {
                    'session_id': session_id,
                    'error': f'Reconciliation encountered an error: {str(e)}',
                    'warning': f'Some matches ({stored_count}) were stored before the error occurred',
                    'summary': {
                        'total_matches': stored_count,
                        'partial_success': True
                    },
                    'diagnostic': {
                        'message': 'Reconciliation encountered an error but some matches were stored',
                        'error': str(e)
                    }
                }
        except Exception:
            pass
        
        # No partial results, return error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run reconciliation: {str(e)}"
        )


@router.get("/sessions/{session_id}/matches")
async def get_session_matches(
    session_id: int = Path(..., description="Session ID"),
    match_type: Optional[str] = Query(None, description="Filter by match type (exact, fuzzy, calculated, inferred)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, modified)"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence score"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List all matches for a session. Tenant-scoped."""
    from app.models.forensic_match import ForensicMatch

    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List all discrepancies for a session. Tenant-scoped."""
    from app.models.forensic_discrepancy import ForensicDiscrepancy

    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Mark a reconciliation session as complete. Tenant-scoped."""
    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    service = ForensicReconciliationService(db)
    success = service.complete_session(
        session_id=session_id,
        auditor_id=current_user.id
    )
    
    return {"message": "Session completed successfully", "session_id": session_id}


# ==================== MATCH ENDPOINTS ====================

@router.post("/matches/{match_id}/approve")
async def approve_match(
    match_id: int = Path(..., description="Match ID"),
    request: Optional[ApproveMatchRequest] = None,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Approve a match. Tenant-scoped."""
    if not get_forensic_match_for_org(db, current_org.id, match_id):
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Reject a match. Tenant-scoped."""
    if not get_forensic_match_for_org(db, current_org.id, match_id):
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Resolve a discrepancy. Tenant-scoped."""
    if not get_forensic_discrepancy_for_org(db, current_org.id, discrepancy_id):
        raise HTTPException(status_code=404, detail=f"Discrepancy {discrepancy_id} not found")
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
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get reconciliation dashboard data. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    service = ForensicReconciliationService(db)
    
    dashboard_data = service.get_reconciliation_dashboard(
        property_id=property_id,
        period_id=period_id
    )
    
    # Add data availability check
    data_availability = service.check_data_availability(property_id, period_id)
    dashboard_data['data_availability'] = data_availability
    
    return dashboard_data


@router.get("/data-availability/{property_id}/{period_id}")
async def check_data_availability(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Check what financial data is available. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    service = ForensicReconciliationService(db)
    return service.check_data_availability(property_id, period_id)


@router.get("/health-score/{property_id}/{period_id}")
async def get_health_score(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    persona: str = Query("controller", description="Persona type (controller, analyst, investor, auditor)"),
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get reconciliation health score. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession

    # Get most recent session
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
    
    # Use new HealthScoreService
    health_service = HealthScoreService(db)
    score_data = health_service.calculate_health_score(session.id, persona=persona)
    
    if 'error' in score_data:
        return score_data
    
    return {
        "property_id": property_id,
        "period_id": period_id,
        "session_id": session.id,
        "persona": persona,
        "health_score": score_data['health_score'],
        "breakdown": score_data['breakdown'],
        "statistics": score_data['statistics']
    }


@router.get("/health-score/{property_id}/trend")
async def get_health_score_trend(
    property_id: int = Path(..., description="Property ID"),
    periods: int = Query(6, description="Number of periods to include"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get health score trend. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    health_service = HealthScoreService(db)
    trend = health_service.get_health_score_trend(property_id, periods=periods)
    
    return {
        "property_id": property_id,
        "trend": trend,
        "periods_included": len(trend)
    }


# ==================== SELF-LEARNING ENDPOINTS ====================

@router.get("/discover-accounts/{property_id}/{period_id}")
async def discover_accounts(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Discover account codes. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    from app.services.account_code_discovery_service import AccountCodeDiscoveryService
    
    service = AccountCodeDiscoveryService(db)
    result = service.discover_all_account_codes(
        property_id=property_id,
        period_id=period_id,
        document_type=document_type
    )
    
    return result


@router.get("/diagnostics/{property_id}/{period_id}")
async def get_diagnostics(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get comprehensive diagnostics. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    service = ForensicReconciliationService(db)
    return service.get_diagnostics(property_id, period_id)


@router.post("/learn-from-match")
async def learn_from_match(
    match_id: int = Body(..., description="Match ID to learn from"),
    feedback: str = Body(..., description="Feedback on the match"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Learn from a match. Tenant-scoped."""
    from app.services.match_learning_service import MatchLearningService

    match = get_forensic_match_for_org(db, current_org.id, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )
    
    learning_service = MatchLearningService(db)
    
    # Analyze this specific match
    result = learning_service.analyze_successful_matches()
    
    return {
        "message": "Learning from match completed",
        "match_id": match_id,
        "patterns_created": result.get('patterns_created', 0),
        "synonyms_created": result.get('synonyms_created', 0)
    }


@router.get("/learned-rules")
async def get_learned_rules(
    source_document_type: Optional[str] = Query(None, description="Filter by source document type"),
    target_document_type: Optional[str] = Query(None, description="Filter by target document type"),
    min_success_rate: float = Query(70.0, description="Minimum success rate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all learned matching rules"""
    from app.services.match_learning_service import MatchLearningService
    
    learning_service = MatchLearningService(db)
    patterns = learning_service.get_learned_patterns(
        source_document_type=source_document_type,
        target_document_type=target_document_type,
        min_success_rate=min_success_rate
    )
    
    return {
        "total": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "pattern_name": p.pattern_name,
                "source_document_type": p.source_document_type,
                "target_document_type": p.target_document_type,
                "source_account_code": p.source_account_code,
                "target_account_code": p.target_account_code,
                "relationship_type": p.relationship_type,
                "success_rate": float(p.success_rate),
                "average_confidence": float(p.average_confidence) if p.average_confidence else 0.0,
                "match_count": p.match_count
            }
            for p in patterns
        ]
    }


@router.post("/suggest-rules")
async def suggest_rules(
    property_id: Optional[int] = Body(None, description="Property ID"),
    period_id: Optional[int] = Body(None, description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """ML suggests new matching rules. Tenant-scoped."""
    if property_id and not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if period_id and not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    from app.services.relationship_discovery_service import RelationshipDiscoveryService
    
    discovery_service = RelationshipDiscoveryService(db)
    result = discovery_service.discover_relationships(
        property_id=property_id,
        period_id=period_id
    )
    
    return {
        "patterns_discovered": result.get('patterns_discovered', 0),
        "correlations_discovered": result.get('correlations_discovered', 0),
        "rules_suggested": result.get('rules_suggested', 0),
        "suggested_rules": result.get('suggested_rules', [])
    }


@router.post("/sessions/{session_id}/validate")
async def validate_session(
    session_id: int = Path(..., description="Session ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Validate matches and calculate health score. Tenant-scoped."""
    session = get_forensic_reconciliation_session_for_org(db, current_org.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    service = ForensicReconciliationService(db)
    
    result = service.validate_matches(session_id=session_id)
    
    if 'error' in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result['error']
        )
    
    return result


# ==================== MATERIALITY ENDPOINTS ====================

class MaterialityConfigCreate(BaseModel):
    """Request model for creating materiality config"""
    property_id: Optional[int] = None
    statement_type: Optional[str] = None
    account_code: Optional[str] = None
    absolute_threshold: float
    relative_threshold_percent: Optional[float] = None
    risk_class: str  # critical, high, medium, low
    tolerance_type: str = "standard"  # strict, standard, loose
    tolerance_absolute: Optional[float] = None
    tolerance_percent: Optional[float] = None
    effective_date: Optional[str] = None
    expires_at: Optional[str] = None


@router.post("/materiality-configs", status_code=status.HTTP_201_CREATED)
async def create_materiality_config(
    request: MaterialityConfigCreate,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Create a new materiality configuration. Tenant-scoped."""
    if request.property_id and not get_property_for_org(db, current_org.id, request.property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    from datetime import date
    
    config = MaterialityConfig(
        property_id=request.property_id,
        statement_type=request.statement_type,
        account_code=request.account_code,
        absolute_threshold=Decimal(str(request.absolute_threshold)),
        relative_threshold_percent=Decimal(str(request.relative_threshold_percent)) if request.relative_threshold_percent else None,
        risk_class=request.risk_class,
        tolerance_type=request.tolerance_type,
        tolerance_absolute=Decimal(str(request.tolerance_absolute)) if request.tolerance_absolute else None,
        tolerance_percent=Decimal(str(request.tolerance_percent)) if request.tolerance_percent else None,
        effective_date=date.fromisoformat(request.effective_date) if request.effective_date else date.today(),
        expires_at=date.fromisoformat(request.expires_at) if request.expires_at else None,
        created_by=current_user.id
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "property_id": config.property_id,
        "statement_type": config.statement_type,
        "account_code": config.account_code,
        "absolute_threshold": float(config.absolute_threshold),
        "relative_threshold_percent": float(config.relative_threshold_percent) if config.relative_threshold_percent else None,
        "risk_class": config.risk_class,
        "tolerance_type": config.tolerance_type
    }


@router.get("/materiality-configs/{property_id}")
async def get_materiality_configs(
    property_id: int = Path(..., description="Property ID"),
    statement_type: Optional[str] = Query(None, description="Filter by statement type"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get materiality configurations for a property. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    from datetime import date
    
    query = db.query(MaterialityConfig).filter(
        MaterialityConfig.property_id == property_id,
        MaterialityConfig.effective_date <= date.today(),
        (MaterialityConfig.expires_at.is_(None) | (MaterialityConfig.expires_at >= date.today()))
    )
    
    if statement_type:
        query = query.filter(MaterialityConfig.statement_type == statement_type)
    
    configs = query.all()
    
    return [
        {
            "id": c.id,
            "property_id": c.property_id,
            "statement_type": c.statement_type,
            "account_code": c.account_code,
            "absolute_threshold": float(c.absolute_threshold),
            "relative_threshold_percent": float(c.relative_threshold_percent) if c.relative_threshold_percent else None,
            "risk_class": c.risk_class,
            "tolerance_type": c.tolerance_type
        }
        for c in configs
    ]


@router.get("/account-risk-classes")
async def get_account_risk_classes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all account risk classes"""
    risk_classes = db.query(AccountRiskClass).filter(
        AccountRiskClass.is_active == True
    ).all()
    
    return [
        {
            "id": rc.id,
            "account_code_pattern": rc.account_code_pattern,
            "account_name_pattern": rc.account_name_pattern,
            "risk_class": rc.risk_class,
            "default_tolerance_absolute": float(rc.default_tolerance_absolute) if rc.default_tolerance_absolute else None,
            "default_tolerance_percent": float(rc.default_tolerance_percent) if rc.default_tolerance_percent else None,
            "reconciliation_frequency": rc.reconciliation_frequency
        }
        for rc in risk_classes
    ]


# ==================== EXCEPTION TIERING ENDPOINTS ====================

@router.post("/matches/{match_id}/classify-tier")
async def classify_match_tier(
    match_id: int = Path(..., description="Match ID"),
    auto_resolve: bool = Query(True, description="Auto-resolve tier 0 matches"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Classify a match into an exception tier. Tenant-scoped."""
    match = get_forensic_match_for_org(db, current_org.id, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )
    
    tiering_service = ExceptionTieringService(db)
    result = tiering_service.classify_and_apply_tiering(match, auto_resolve=auto_resolve)
    
    return result


@router.post("/matches/{match_id}/suggest-fix")
async def suggest_match_fix(
    match_id: int = Path(..., description="Match ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get suggested fix for a tier 1 match. Tenant-scoped."""
    match = get_forensic_match_for_org(db, current_org.id, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )
    
    tiering_service = ExceptionTieringService(db)
    result = tiering_service.suggest_tier_1_fix(match)
    
    return result


@router.post("/matches/bulk-tier")
async def bulk_classify_tiers(
    match_ids: List[int] = Body(..., description="List of match IDs"),
    auto_resolve: bool = Body(True, description="Auto-resolve tier 0 matches"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Bulk classify matches into exception tiers. Tenant-scoped."""
    from app.models.forensic_match import ForensicMatch
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession

    matches = (
        db.query(ForensicMatch)
        .join(ForensicReconciliationSession, ForensicMatch.session_id == ForensicReconciliationSession.id)
        .join(Property, ForensicReconciliationSession.property_id == Property.id)
        .filter(
            ForensicMatch.id.in_(match_ids),
            Property.organization_id == current_org.id,
        )
        .all()
    )
    
    tiering_service = ExceptionTieringService(db)
    results = []
    
    for match in matches:
        try:
            result = tiering_service.classify_and_apply_tiering(match, auto_resolve=auto_resolve)
            results.append(result)
        except Exception as e:
            results.append({
                'match_id': match.id,
                'success': False,
                'error': str(e)
            })
    
    return {
        'total': len(matches),
        'processed': len(results),
        'results': results
    }


# ==================== AUTO-RESOLUTION RULES ENDPOINTS ====================

class AutoResolutionRuleCreate(BaseModel):
    """Request model for creating auto-resolution rule"""
    rule_name: str
    pattern_type: str  # rounding, timing, synonym, mapping
    condition_json: dict
    action_type: str  # auto_close, suggest_fix, route_to_queue
    suggested_mapping: Optional[dict] = None
    confidence_threshold: float
    property_id: Optional[int] = None
    statement_type: Optional[str] = None
    description: Optional[str] = None
    priority: int = 0


@router.get("/auto-resolution-rules")
async def list_auto_resolution_rules(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List auto-resolution rules. Tenant-scoped."""
    query = db.query(AutoResolutionRule).filter(
        AutoResolutionRule.is_active == True
    )
    
    if property_id:
        if not get_property_for_org(db, current_org.id, property_id):
            return []
        query = query.filter(
            (AutoResolutionRule.property_id == property_id) |
            (AutoResolutionRule.property_id.is_(None))
        )
    
    if pattern_type:
        query = query.filter(AutoResolutionRule.pattern_type == pattern_type)
    
    rules = query.order_by(AutoResolutionRule.priority.desc()).all()
    
    return [
        {
            "id": r.id,
            "rule_name": r.rule_name,
            "pattern_type": r.pattern_type,
            "condition_json": r.condition_json,
            "action_type": r.action_type,
            "suggested_mapping": r.suggested_mapping,
            "confidence_threshold": float(r.confidence_threshold),
            "property_id": r.property_id,
            "statement_type": r.statement_type,
            "priority": r.priority,
            "description": r.description
        }
        for r in rules
    ]


@router.post("/auto-resolution-rules", status_code=status.HTTP_201_CREATED)
async def create_auto_resolution_rule(
    request: AutoResolutionRuleCreate,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Create a new auto-resolution rule. Tenant-scoped."""
    if request.property_id and not get_property_for_org(db, current_org.id, request.property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    
    rule = AutoResolutionRule(
        rule_name=request.rule_name,
        pattern_type=request.pattern_type,
        condition_json=request.condition_json,
        action_type=request.action_type,
        suggested_mapping=request.suggested_mapping,
        confidence_threshold=Decimal(str(request.confidence_threshold)),
        property_id=request.property_id,
        statement_type=request.statement_type,
        description=request.description,
        priority=request.priority,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "pattern_type": rule.pattern_type,
        "action_type": rule.action_type,
        "confidence_threshold": float(rule.confidence_threshold)
    }


# ==================== CHART OF ACCOUNTS ENDPOINTS ====================

@router.get("/account-synonyms")
async def get_account_synonyms(
    account_name: Optional[str] = Query(None, description="Search by account name"),
    account_code: Optional[str] = Query(None, description="Filter by account code"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get account synonyms"""
    service = ChartOfAccountsService(db)
    
    if account_name:
        synonyms = service.find_synonyms(account_name, account_code)
        return synonyms
    
    # Return all active synonyms
    synonyms = db.query(AccountSynonym).filter(
        AccountSynonym.is_active == True
    ).limit(100).all()
    
    return [
        {
            "id": s.id,
            "account_code": s.account_code,
            "synonym": s.synonym,
            "canonical_name": s.canonical_name,
            "confidence": float(s.confidence),
            "source": s.source
        }
        for s in synonyms
    ]


@router.post("/account-synonyms", status_code=status.HTTP_201_CREATED)
async def create_account_synonym(
    synonym: str = Body(..., description="Synonym text"),
    canonical_name: str = Body(..., description="Canonical account name"),
    account_code: Optional[str] = Body(None, description="Account code"),
    confidence: float = Body(100.0, description="Confidence score"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new account synonym"""
    service = ChartOfAccountsService(db)
    result = service.add_synonym(synonym, canonical_name, account_code, confidence)
    
    return {
        "id": result.id,
        "synonym": result.synonym,
        "canonical_name": result.canonical_name,
        "account_code": result.account_code,
        "confidence": float(result.confidence)
    }


@router.get("/account-mappings/suggest")
async def suggest_account_mappings(
    source_account_code: str = Query(..., description="Source account code"),
    source_document_type: Optional[str] = Query(None, description="Source document type"),
    target_document_type: Optional[str] = Query(None, description="Target document type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get suggested account mappings based on historical approvals"""
    service = ChartOfAccountsService(db)
    suggestions = service.suggest_mapping(
        source_account_code,
        source_document_type=source_document_type,
        target_document_type=target_document_type
    )
    
    return suggestions


@router.post("/account-mappings/approve")
async def approve_account_mapping(
    source_account_code: str = Body(..., description="Source account code"),
    target_account_code: str = Body(..., description="Target account code"),
    source_document_type: Optional[str] = Body(None, description="Source document type"),
    target_document_type: Optional[str] = Body(None, description="Target document type"),
    mapping_type: str = Body("exact", description="Mapping type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record approval of an account mapping (learns from user decisions)"""
    service = ChartOfAccountsService(db)
    mapping = service.record_approval(
        source_account_code,
        target_account_code,
        source_document_type,
        target_document_type,
        mapping_type,
        approved_by=current_user.id
    )
    
    return {
        "id": mapping.id,
        "source_account_code": mapping.source_account_code,
        "target_account_code": mapping.target_account_code,
        "confidence": float(mapping.confidence_score),
        "approved_count": mapping.approved_count
    }


# ==================== CALCULATED RULES ENDPOINTS ====================

class CalculatedRuleCreate(BaseModel):
    """Request model for creating calculated rule"""
    rule_id: str
    rule_name: str
    formula: str
    description: Optional[str] = None
    property_scope: Optional[dict] = None  # JSON: property IDs or "all"
    doc_scope: dict  # JSON: document types
    tolerance_absolute: Optional[float] = None
    tolerance_percent: Optional[float] = None
    materiality_threshold: Optional[float] = None
    severity: str = "medium"  # critical, high, medium, low
    failure_explanation_template: Optional[str] = None
    effective_date: Optional[str] = None
    expires_at: Optional[str] = None


class CalculatedRuleEvaluation(BaseModel):
    """Evaluation result for a calculated rule"""
    rule_id: str
    rule_name: str
    description: Optional[str] = None
    formula: str
    severity: str
    status: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    difference_percent: Optional[float] = None
    tolerance_absolute: Optional[float] = None
    tolerance_percent: Optional[float] = None
    message: Optional[str] = None


@router.get("/calculated-rules")
async def list_calculated_rules(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List all calculated rules. Tenant-scoped."""
    engine = CalculatedRulesEngine(db)
    
    if property_id:
        if not get_property_for_org(db, current_org.id, property_id):
            return []
        rules = engine.get_active_rules(property_id)
    else:
        # Get all active rules
        from datetime import date
        rules = db.query(CalculatedRule).filter(
            and_(
                CalculatedRule.is_active == True,
                CalculatedRule.effective_date <= date.today(),
                (CalculatedRule.expires_at.is_(None) | (CalculatedRule.expires_at >= date.today()))
            )
        ).order_by(CalculatedRule.rule_id, CalculatedRule.version.desc()).all()
        
        # Deduplicate by rule_id
        seen = set()
        unique_rules = []
        for rule in rules:
            if rule.rule_id not in seen:
                seen.add(rule.rule_id)
                unique_rules.append(rule)
        rules = unique_rules
    
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "version": r.version,
            "rule_name": r.rule_name,
            "formula": r.formula,
            "description": r.description,
            "tolerance_absolute": float(r.tolerance_absolute) if r.tolerance_absolute else None,
            "tolerance_percent": float(r.tolerance_percent) if r.tolerance_percent else None,
            "severity": r.severity,
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None
        }
        for r in rules
    ]


@router.get("/document-health/{property_id}/{period_id}")
async def get_document_health(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get document health scores. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")

    # Map rule prefixes to document types
    rule_prefix_map = {
        'BS': 'balance_sheet',
        'IS': 'income_statement',
        'CF': 'cash_flow',
        'RR': 'rent_roll',
        'MST': 'mortgage_statement',  # Mortgage rules use MST- prefix, not MS-
        '3S': 'three_statement_integration'  # Three statement integration rules use 3S- prefix
    }
    
    document_health = {}
    
    # Calculate health from calculated rules
    try:
        query = text("""
            SELECT 
                rule_code,
                status
            FROM cross_document_reconciliations
            WHERE property_id = :property_id 
              AND period_id = :period_id
        """)
        
        results = db.execute(query, {
            "property_id": property_id,
            "period_id": period_id
        }).fetchall()
        
        # Group by document type
        doc_stats = {
            'balance_sheet': {'total': 0, 'passed': 0},
            'income_statement': {'total': 0, 'passed': 0},
            'cash_flow': {'total': 0, 'passed': 0},
            'rent_roll': {'total': 0, 'passed': 0},
            'mortgage_statement': {'total': 0, 'passed': 0}
        }
        
        for row in results:
            rule_code = row[0] or ''
            status = row[1] or ''
            
            # Extract prefix (e.g., "BS-1" -> "BS")
            prefix = rule_code.split('-')[0] if '-' in rule_code else ''
            
            doc_type = rule_prefix_map.get(prefix)
            if doc_type and doc_type in doc_stats:
                doc_stats[doc_type]['total'] += 1
                if status == 'PASS':
                    doc_stats[doc_type]['passed'] += 1
        
        # Calculate health percentages
        for doc_type, stats in doc_stats.items():
            if stats['total'] > 0:
                health_pct = (stats['passed'] / stats['total']) * 100
                document_health[doc_type] = {
                    'health_score': round(health_pct, 2),
                    'total_rules': stats['total'],
                    'passed_rules': stats['passed'],
                    'failed_rules': stats['total'] - stats['passed']
                }
            else:
                # No rules for this document type
                document_health[doc_type] = {
                    'health_score': 0.0,
                    'total_rules': 0,
                    'passed_rules': 0,
                    'failed_rules': 0
                }
    
    except Exception as e:
        logger.error(f"Error calculating document health: {str(e)}")
        # Return default structure on error
        for doc_type in rule_prefix_map.values():
            document_health[doc_type] = {
                'health_score': 0.0,
                'total_rules': 0,
                'passed_rules': 0,
                'failed_rules': 0,
                'error': str(e)
            }
    
    # Calculate overall health
    valid_scores = [v['health_score'] for v in document_health.values() if v['total_rules'] > 0]
    overall_health = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 0.0
    
    return {
        "property_id": property_id,
        "period_id": period_id,
        "overall_health": overall_health,
        "documents": document_health
    }


@router.get("/calculated-rules/evaluate/{property_id}/{period_id}")
@router.post("/calculated-rules/evaluate/{property_id}/{period_id}")
async def evaluate_calculated_rules(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    request: Optional[RunReconciliationRequest] = Body(None),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Evaluate all calculated rules. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    # MODIFIED: Fetch results from the new ReconciliationRuleEngine storage
    # instead of calculating on-the-fly with Legacy engine
    
    results = []
    
    try:
        # Query results from the new table
        query = text("""
            SELECT 
                rule_code, 
                reconciliation_type as rule_name,
                explanation as message,
                status,
                source_value as actual_value,
                target_value as expected_value,
                difference,
                is_material,
                created_at,
                recommendation as formula
            FROM cross_document_reconciliations
            WHERE property_id = :p_id AND period_id = :period_id
        """)
        
        db_results = db.execute(query, {"p_id": property_id, "period_id": period_id}).fetchall()
        
        for row in db_results:
            # Map DB columns to Frontend expected format
            status_val = row.status if row.status else "SKIPPED"
            
            # Calculate percent if possible
            diff = float(row.difference or 0)
            expected = float(row.expected_value or 0)
            actual = float(row.actual_value or 0)
            
            diff_percent = 0.0
            if max(abs(expected), abs(actual)) > 0:
                diff_percent = (diff / max(abs(expected), abs(actual))) * 100
                
            results.append({
                "rule_id": row.rule_code or "UNKNOWN",
                "rule_name": row.rule_name or "Unknown Rule",
                "description": row.message, # Use explanation as description/message
                "formula": row.formula or "N/A (Python Rule)", 
                "severity": "medium", # Default
                "status": status_val, 
                "expected_value": expected,
                "actual_value": actual,
                "difference": diff,
                "difference_percent": diff_percent,
                "tolerance_absolute": 0.01,
                "tolerance_percent": 5.0,
                "message": row.message
            })
            
    except Exception as e:
        # Fallback or Log error
        print(f"Error fetching reconciliation results: {e}")
        pass

    return {
        "property_id": property_id,
        "period_id": period_id,
        "total": len(results),
        "passed": len([r for r in results if r.get("status") == "PASS"]),
        "failed": len([r for r in results if r.get("status") == "FAIL"]),
        "skipped": len([r for r in results if r.get("status") == "SKIPPED"]),
        "rules": results
    }


@router.post("/calculated-rules", status_code=status.HTTP_201_CREATED)
async def create_calculated_rule(
    request: CalculatedRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new calculated rule (creates new version if rule_id exists)"""
    from datetime import date
    
    # Get latest version for this rule_id
    latest = db.query(CalculatedRule).filter(
        CalculatedRule.rule_id == request.rule_id
    ).order_by(CalculatedRule.version.desc()).first()
    
    new_version = (latest.version + 1) if latest else 1
    
    rule = CalculatedRule(
        rule_id=request.rule_id,
        version=new_version,
        rule_name=request.rule_name,
        formula=request.formula,
        description=request.description,
        property_scope=request.property_scope,
        doc_scope=request.doc_scope,
        tolerance_absolute=Decimal(str(request.tolerance_absolute)) if request.tolerance_absolute else None,
        tolerance_percent=Decimal(str(request.tolerance_percent)) if request.tolerance_percent else None,
        materiality_threshold=Decimal(str(request.materiality_threshold)) if request.materiality_threshold else None,
        severity=request.severity,
        failure_explanation_template=request.failure_explanation_template,
        effective_date=date.fromisoformat(request.effective_date) if request.effective_date else date.today(),
        expires_at=date.fromisoformat(request.expires_at) if request.expires_at else None,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "version": rule.version,
        "rule_name": rule.rule_name
    }


@router.post("/calculated-rules/{rule_id}/test")
async def test_calculated_rule(
    rule_id: str = Path(..., description="Rule ID"),
    property_id: int = Body(..., description="Property ID"),
    period_id: int = Body(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Test a calculated rule. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    engine = CalculatedRulesEngine(db)
    
    # Get latest version of rule
    rule = db.query(CalculatedRule).filter(
        CalculatedRule.rule_id == rule_id
    ).order_by(CalculatedRule.version.desc()).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    result = engine.evaluate_rule(rule, property_id, period_id)
    
    if not result:
        return {
            "success": False,
            "message": "Rule could not be evaluated"
        }

    return {
        "success": result.get("status") != "SKIPPED",
        "evaluation": result
    }


@router.get("/calculated-rules/detail/{rule_id}/{property_id}/{period_id}")
async def get_calculated_rule_detail(
    rule_id: str = Path(..., description="Rule ID (e.g. BS-1)"),
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Period ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get detailed execution result. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    if not get_period_for_org(db, current_org.id, period_id):
        raise HTTPException(status_code=404, detail="Period not found")
    
    # 1. Try to find the execution result in cross_document_reconciliations
    query = text("""
        SELECT 
            rule_code, 
            reconciliation_type as rule_name,
            explanation as message,
            status,
            source_value as actual_value,
            target_value as expected_value,
            difference,
            is_material,
            created_at,
            recommendation as formula,
            id
        FROM cross_document_reconciliations
        WHERE property_id = :p_id 
          AND period_id = :period_id
          AND rule_code = :rule_id
    """)
    
    row = db.execute(query, {
        "p_id": property_id, 
        "period_id": period_id,
        "rule_id": rule_id
    }).fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule execution not found for {rule_id}"
        )

    # 2. Get history (last 6 periods)
    history_query = text("""
        SELECT 
            fp.period_name,
            fp.period_year,
            fp.period_month,
            cdr.status,
            cdr.difference
        FROM cross_document_reconciliations cdr
        JOIN financial_periods fp ON cdr.period_id = fp.id
        WHERE cdr.property_id = :p_id 
          AND cdr.rule_code = :rule_id
          AND fp.id <= :period_id
        ORDER BY fp.period_year DESC, fp.period_month DESC
        LIMIT 6
    """)
    
    history_rows = db.execute(history_query, {
        "p_id": property_id,
        "period_id": period_id,
        "rule_id": rule_id
    }).fetchall()
    
    history = []
    for h in history_rows:
        history.append({
            "period": h.period_name or f"{h.period_year}-{h.period_month:02d}",
            "status": h.status,
            "variance": float(h.difference or 0)
        })

    # 3. Construct response
    status_val = row.status if row.status else "SKIPPED"
    diff = float(row.difference or 0)
    expected = float(row.expected_value or 0)
    actual = float(row.actual_value or 0)
    
    return {
        "id": row.rule_code,
        "name": row.rule_name,
        "description": row.message,
        "formula": row.formula or "Standard Validation Rule",
        "status": status_val,
        "type": "Calculated Rule",
        "lastRun": row.created_at.isoformat() if row.created_at else None,
        "variance": diff,
        "threshold": 0.01, # Default or fetch from config
        "sourceData": {
            "account": "Source Value",
            "value": actual,
            "date": "Current Period"
        },
        "targetData": {
            "account": "Target / Expected",
            "value": expected,
            "date": "Current Period"
        },
        "history": history
    }

# ==================== HEALTH SCORE CONFIGURATION ENDPOINTS ====================

class HealthScoreConfigUpdate(BaseModel):
    """Request model for updating health score config"""
    weights_json: dict
    trend_weight: Optional[float] = None
    volatility_weight: Optional[float] = None
    blocked_close_rules: Optional[list] = None
    description: Optional[str] = None


@router.get("/health-score-configs/{persona}")
async def get_health_score_config(
    persona: str = Path(..., description="Persona type (controller, analyst, investor, auditor)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get health score configuration for a persona"""
    health_service = HealthScoreService(db)
    config = health_service.get_config(persona)
    
    return config


@router.put("/health-score-configs/{persona}")
async def update_health_score_config(
    persona: str = Path(..., description="Persona type"),
    request: HealthScoreConfigUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update health score configuration for a persona"""
    config = db.query(HealthScoreConfig).filter(
        HealthScoreConfig.persona == persona
    ).first()
    
    if config:
        # Update existing
        config.weights_json = request.weights_json
        config.trend_weight = Decimal(str(request.trend_weight)) if request.trend_weight else None
        config.volatility_weight = Decimal(str(request.volatility_weight)) if request.volatility_weight else None
        config.blocked_close_rules = request.blocked_close_rules
        config.description = request.description
    else:
        # Create new
        config = HealthScoreConfig(
            persona=persona,
            weights_json=request.weights_json,
            trend_weight=Decimal(str(request.trend_weight)) if request.trend_weight else None,
            volatility_weight=Decimal(str(request.volatility_weight)) if request.volatility_weight else None,
            blocked_close_rules=request.blocked_close_rules,
            description=request.description
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    
    return {
        "persona": config.persona,
        "weights": config.weights_json,
        "trend_weight": float(config.trend_weight) if config.trend_weight else None,
        "volatility_weight": float(config.volatility_weight) if config.volatility_weight else None,
        "blocked_close_rules": config.blocked_close_rules
    }
