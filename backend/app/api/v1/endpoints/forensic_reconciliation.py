"""
Forensic Reconciliation API Endpoints
Complete Big 5-level cross-document reconciliation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.services.complete_forensic_reconciliation_service import CompleteForensicReconciliationService
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


# ============================================================================
# Pydantic Response Models
# ============================================================================

class PropertyInfo(BaseModel):
    property_id: int
    property_code: str
    property_name: str
    period_id: int
    period_year: int
    period_month: int
    period_label: str


class DocumentCompleteness(BaseModel):
    documents_required: int
    documents_present: int
    documents_missing: int
    completeness_pct: float
    documents: dict
    status: str


class TieOutResult(BaseModel):
    tieout_id: int
    priority: str
    name: str
    source_field: str
    source_value: float
    target_field: str
    target_value: float
    variance: float
    tolerance: float
    status: str
    severity: str


class BusinessMetric(BaseModel):
    value: Optional[float] = None
    status: str
    threshold_pass: Optional[float] = None
    threshold_warning: Optional[float] = None


class RedFlag(BaseModel):
    category: str
    severity: str
    description: str
    value: Optional[float] = None
    impact: str


class AuditOpinion(BaseModel):
    opinion: str
    explanation: str
    critical_tieouts_passed: int
    critical_tieouts_total: int
    pass_rate: float
    overall_quality_score: float
    issued_by: str
    issued_at: str


class ForensicReconciliationReport(BaseModel):
    property_info: PropertyInfo
    document_completeness: DocumentCompleteness
    balance_sheet: dict
    income_statement: dict
    cash_flow: dict
    rent_roll: dict
    mortgage_statement: dict
    critical_tieouts: List[TieOutResult]
    warning_tieouts: List[TieOutResult]
    informational_tieouts: List[TieOutResult]
    business_metrics: dict
    variance_analysis: List[dict]
    red_flags: List[RedFlag]
    audit_opinion: AuditOpinion
    overall_assessment: dict
    generated_at: str
    report_version: str


class ReconciliationHistory(BaseModel):
    period_id: int
    period_label: str
    audit_opinion: str
    critical_tieouts_passed: int
    dscr: Optional[float] = None
    dscr_status: str
    occupancy_rate: Optional[float] = None
    quality_score: float


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/refresh-views", summary="Refresh Materialized Views")
def refresh_materialized_views(
    db: Session = Depends(get_db)
):
    """
    Refresh all forensic reconciliation materialized views.

    Call this endpoint:
    - After uploading new financial documents
    - Before running reconciliation reports
    - On a scheduled basis (e.g., hourly or daily)

    Returns:
        Status of view refresh operation
    """
    try:
        service = CompleteForensicReconciliationService(db)
        service.refresh_materialized_views()

        return {
            "status": "success",
            "message": "All materialized views refreshed successfully",
            "views_refreshed": [
                "balance_sheet_summary",
                "income_statement_summary",
                "cash_flow_summary",
                "forensic_reconciliation_master"
            ],
            "refreshed_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh views: {str(e)}"
        )


@router.get(
    "/reconcile/{property_id}/{period_id}",
    response_model=ForensicReconciliationReport,
    summary="Complete Forensic Reconciliation"
)
def perform_complete_reconciliation(
    property_id: int,
    period_id: int,
    refresh_views: bool = Query(
        default=True,
        description="Refresh materialized views before reconciliation"
    ),
    db: Session = Depends(get_db)
):
    """
    Perform complete Big 5-level forensic reconciliation.

    This endpoint performs:
    - Document completeness check (5 documents)
    - All 12 cross-document tie-outs (5 critical, 5 warning, 2 informational)
    - Business metrics calculation (DSCR, occupancy, NOI, cash coverage)
    - Variance analysis
    - Red flag detection
    - Audit opinion generation

    Parameters:
    - **property_id**: Property ID
    - **period_id**: Financial period ID
    - **refresh_views**: Whether to refresh views before reconciliation (default: true)

    Returns:
        Complete forensic reconciliation report with audit opinion
    """
    try:
        service = CompleteForensicReconciliationService(db)
        report = service.perform_complete_reconciliation(
            property_id=property_id,
            period_id=period_id,
            refresh_views=refresh_views
        )

        if report.get('status') == 'error':
            raise HTTPException(
                status_code=404,
                detail=report.get('message', 'Data not found')
            )

        return report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation failed: {str(e)}"
        )


@router.get(
    "/reconcile/{property_id}/year/{year}/month/{month}",
    response_model=ForensicReconciliationReport,
    summary="Reconcile by Year/Month"
)
def reconcile_by_year_month(
    property_id: int,
    year: int,
    month: int,
    refresh_views: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """
    Perform reconciliation using year and month instead of period_id.

    Parameters:
    - **property_id**: Property ID
    - **year**: Year (e.g., 2023)
    - **month**: Month (1-12)
    - **refresh_views**: Whether to refresh views

    Returns:
        Complete forensic reconciliation report
    """
    from sqlalchemy import text

    # Find period_id from year/month
    query = text("""
        SELECT id FROM financial_periods
        WHERE property_id = :property_id
        AND period_year = :year
        AND period_month = :month
    """)

    result = db.execute(
        query,
        {'property_id': property_id, 'year': year, 'month': month}
    ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Period not found for {year}-{month:02d}"
        )

    period_id = result[0]

    return perform_complete_reconciliation(
        property_id=property_id,
        period_id=period_id,
        refresh_views=refresh_views,
        db=db
    )


@router.get(
    "/summary/{property_id}/{period_id}",
    summary="Reconciliation Summary (Fast)"
)
def get_reconciliation_summary(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get quick reconciliation summary from master view (no view refresh).

    Use this for dashboards and quick checks.
    For complete analysis, use the /reconcile endpoint.

    Returns:
        Summary with key metrics and tie-out statuses
    """
    try:
        service = CompleteForensicReconciliationService(db)
        data = service.get_reconciliation_summary(property_id, period_id)

        if not data:
            raise HTTPException(
                status_code=404,
                detail="No reconciliation data found"
            )

        # Return key metrics only
        return {
            "property_id": data['property_id'],
            "property_code": data['property_code'],
            "period_label": f"{data['period_year']}-{data['period_month']:02d}",
            "audit_opinion": data['audit_opinion'],
            "critical_tieouts_passed": data['critical_tieouts_passed'],
            "critical_tieouts_total": 5,
            "dscr": float(data['dscr']) if data.get('dscr') else None,
            "dscr_status": data['dscr_status'],
            "occupancy_rate": float(data['occupancy_rate']) if data.get('occupancy_rate') else None,
            "occupancy_status": data['occupancy_status'],
            "noi": float(data['noi']) if data.get('noi') else None,
            "noi_status": data['noi_status'],
            "overall_quality_score": float(data['overall_quality_score']) if data.get('overall_quality_score') else 0,
            "tieout_statuses": {
                "mortgage_to_balance_sheet": data.get('tieout_1_status'),
                "mortgage_to_cash_flow": data.get('tieout_2_status'),
                "cash_flow_to_balance_sheet": data.get('tieout_3_status'),
                "balance_sheet_equation": data.get('tieout_4_status'),
                "cash_flow_reconciliation": data.get('tieout_5_status'),
                "rent_roll_to_income_stmt": data.get('tieout_6_status'),
                "mortgage_interest_to_income_stmt": data.get('tieout_7_status')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get(
    "/history/{property_id}",
    response_model=List[ReconciliationHistory],
    summary="Reconciliation History"
)
def get_reconciliation_history(
    property_id: int,
    limit: int = Query(default=12, ge=1, le=60, description="Number of periods to return"),
    db: Session = Depends(get_db)
):
    """
    Get reconciliation history for a property.

    Returns the last N periods with key metrics for trend analysis.

    Parameters:
    - **property_id**: Property ID
    - **limit**: Number of periods to return (default: 12, max: 60)

    Returns:
        List of historical reconciliation summaries
    """
    try:
        service = CompleteForensicReconciliationService(db)
        history = service.get_reconciliation_history(
            property_id=property_id,
            limit=limit
        )

        return history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history: {str(e)}"
        )


@router.get(
    "/tieouts/{property_id}/{period_id}",
    summary="Tie-Out Details Only"
)
def get_tieout_details(
    property_id: int,
    period_id: int,
    priority: Optional[str] = Query(
        default=None,
        description="Filter by priority: CRITICAL, WARNING, or INFORMATIONAL"
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: PASS, WARNING, or FAIL"
    ),
    db: Session = Depends(get_db)
):
    """
    Get detailed tie-out results only (without full reconciliation).

    Use this for focused tie-out analysis.

    Parameters:
    - **property_id**: Property ID
    - **period_id**: Financial period ID
    - **priority**: Filter by priority level
    - **status**: Filter by status

    Returns:
        All tie-out results with optional filtering
    """
    try:
        service = CompleteForensicReconciliationService(db)

        # Get full report (cached from view, so fast)
        report = service.perform_complete_reconciliation(
            property_id=property_id,
            period_id=period_id,
            refresh_views=False  # Don't refresh for quick query
        )

        if report.get('status') == 'error':
            raise HTTPException(status_code=404, detail=report.get('message'))

        # Combine all tie-outs
        all_tieouts = (
            report['critical_tieouts'] +
            report['warning_tieouts'] +
            report['informational_tieouts']
        )

        # Apply filters
        if priority:
            all_tieouts = [t for t in all_tieouts if t['priority'] == priority.upper()]

        if status:
            all_tieouts = [t for t in all_tieouts if t['status'] == status.upper()]

        return {
            "property_id": property_id,
            "period_id": period_id,
            "period_label": report['property_info']['period_label'],
            "total_tieouts": len(all_tieouts),
            "filters": {
                "priority": priority,
                "status": status
            },
            "tieouts": all_tieouts
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tie-out details: {str(e)}"
        )


@router.get(
    "/business-metrics/{property_id}/{period_id}",
    summary="Business Metrics Only"
)
def get_business_metrics(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get business metrics only (DSCR, occupancy, NOI, etc.).

    Use this for KPI dashboards and executive summaries.

    Parameters:
    - **property_id**: Property ID
    - **period_id**: Financial period ID

    Returns:
        Business metrics including DSCR, occupancy, and NOI
    """
    try:
        service = CompleteForensicReconciliationService(db)

        report = service.perform_complete_reconciliation(
            property_id=property_id,
            period_id=period_id,
            refresh_views=False
        )

        if report.get('status') == 'error':
            raise HTTPException(status_code=404, detail=report.get('message'))

        return {
            "property_id": property_id,
            "period_id": period_id,
            "period_label": report['property_info']['period_label'],
            "metrics": report['business_metrics'],
            "overall_assessment": report['overall_assessment']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get business metrics: {str(e)}"
        )


@router.get(
    "/red-flags/{property_id}",
    summary="Red Flags Across All Periods"
)
def get_property_red_flags(
    property_id: int,
    limit: int = Query(default=12, ge=1, le=60),
    db: Session = Depends(get_db)
):
    """
    Get all red flags for a property across multiple periods.

    Use this for risk assessment and audit planning.

    Parameters:
    - **property_id**: Property ID
    - **limit**: Number of periods to check (default: 12)

    Returns:
        All red flags found across specified periods
    """
    try:
        service = CompleteForensicReconciliationService(db)

        # Get history to find periods
        history = service.get_reconciliation_history(property_id, limit)

        all_red_flags = []

        for period in history:
            report = service.perform_complete_reconciliation(
                property_id=property_id,
                period_id=period['period_id'],
                refresh_views=False
            )

            if report.get('red_flags'):
                for flag in report['red_flags']:
                    flag['period_label'] = period['period_label']
                    flag['period_id'] = period['period_id']
                    all_red_flags.append(flag)

        # Group by severity
        critical = [f for f in all_red_flags if f['severity'] == 'CRITICAL']
        warnings = [f for f in all_red_flags if f['severity'] == 'WARNING']

        return {
            "property_id": property_id,
            "periods_analyzed": len(history),
            "total_red_flags": len(all_red_flags),
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "critical_red_flags": critical,
            "warning_red_flags": warnings,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get red flags: {str(e)}"
        )
