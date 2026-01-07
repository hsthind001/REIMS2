"""
Mortgage Statement API - Manage mortgage statements and related metrics
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

from app.db.database import get_db
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.mortgage_payment_history import MortgagePaymentHistory
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.financial_metrics import FinancialMetrics
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.services.metrics_service import MetricsService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== REQUEST/RESPONSE MODELS ====================

class MortgageStatementResponse(BaseModel):
    """Basic mortgage statement response"""
    id: int
    property_id: int
    period_id: int
    upload_id: Optional[int] = None
    lender_id: Optional[int] = None
    
    loan_number: str
    loan_type: Optional[str] = None
    property_address: Optional[str] = None
    borrower_name: Optional[str] = None
    
    statement_date: date
    payment_due_date: Optional[date] = None
    
    principal_balance: float
    total_loan_balance: Optional[float] = None
    total_payment_due: Optional[float] = None
    
    interest_rate: Optional[float] = None
    maturity_date: Optional[date] = None
    
    annual_debt_service: Optional[float] = None
    monthly_debt_service: Optional[float] = None
    
    extraction_confidence: Optional[float] = None
    needs_review: bool
    has_errors: bool
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class MortgageStatementDetailResponse(MortgageStatementResponse):
    """Detailed mortgage statement with payment history"""
    # Current Balances
    tax_escrow_balance: Optional[float] = None
    insurance_escrow_balance: Optional[float] = None
    reserve_balance: Optional[float] = None
    suspense_balance: Optional[float] = None
    
    # Payment Breakdown
    principal_due: Optional[float] = None
    interest_due: Optional[float] = None
    tax_escrow_due: Optional[float] = None
    insurance_escrow_due: Optional[float] = None
    reserve_due: Optional[float] = None
    late_fees: Optional[float] = None
    other_fees: Optional[float] = None
    
    # YTD Totals
    ytd_principal_paid: Optional[float] = None
    ytd_interest_paid: Optional[float] = None
    ytd_total_paid: Optional[float] = None
    
    # Loan Terms
    original_loan_amount: Optional[float] = None
    loan_term_months: Optional[int] = None
    remaining_term_months: Optional[int] = None
    payment_frequency: Optional[str] = None
    amortization_type: Optional[str] = None
    
    # Payment History
    payment_history: List[dict] = []
    
    class Config:
        from_attributes = True


class DSCRHistoryResponse(BaseModel):
    """DSCR history over time"""
    property_id: int
    property_code: str
    history: List[dict]
    
    class Config:
        from_attributes = True


class LTVHistoryResponse(BaseModel):
    """LTV history over time"""
    property_id: int
    property_code: str
    history: List[dict]
    
    class Config:
        from_attributes = True


class DebtSummaryResponse(BaseModel):
    """Comprehensive debt summary"""
    property_id: int
    period_id: int
    total_mortgage_debt: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    total_monthly_debt_service: Optional[float] = None
    total_annual_debt_service: Optional[float] = None
    dscr: Optional[float] = None
    interest_coverage_ratio: Optional[float] = None
    debt_yield: Optional[float] = None
    break_even_occupancy: Optional[float] = None
    mortgage_count: int = 0
    mortgages: List[MortgageStatementResponse] = []
    
    class Config:
        from_attributes = True


class CovenantMonitoringResponse(BaseModel):
    """Covenant compliance status"""
    property_id: int
    property_code: str
    dscr: Optional[float] = None
    dscr_status: str  # "healthy", "warning", "critical"
    ltv: Optional[float] = None
    ltv_status: str  # "compliant", "warning", "breach"
    covenant_compliant: bool
    active_alerts: int = 0
    active_locks: int = 0
    
    class Config:
        from_attributes = True


class MaturityCalendarResponse(BaseModel):
    """Loan maturity calendar"""
    upcoming_maturities: List[dict]
    total_upcoming: int
    
    class Config:
        from_attributes = True


# ==================== ENDPOINTS ====================

@router.get("/properties/{property_id}/periods/{period_id}", response_model=List[MortgageStatementResponse])
def get_mortgages_by_property_period(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Financial Period ID"),
    db: Session = Depends(get_db)
):
    """
    Get all mortgage statements for a property and period
    """
    mortgages = db.query(MortgageStatementData).filter(
        MortgageStatementData.property_id == property_id,
        MortgageStatementData.period_id == period_id
    ).all()
    
    return mortgages


@router.get("/{mortgage_id}", response_model=MortgageStatementDetailResponse)
def get_mortgage_detail(
    mortgage_id: int = Path(..., description="Mortgage Statement ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed mortgage statement with payment history
    """
    mortgage = db.query(MortgageStatementData).filter(
        MortgageStatementData.id == mortgage_id
    ).first()
    
    if not mortgage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mortgage statement {mortgage_id} not found"
        )
    
    # Get payment history
    payment_history = db.query(MortgagePaymentHistory).filter(
        MortgagePaymentHistory.mortgage_id == mortgage_id
    ).order_by(MortgagePaymentHistory.payment_date.desc()).all()
    
    # Convert to dict for response
    payment_history_dicts = [
        {
            "id": p.id,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "payment_number": p.payment_number,
            "principal_paid": float(p.principal_paid) if p.principal_paid else None,
            "interest_paid": float(p.interest_paid) if p.interest_paid else None,
            "escrow_paid": float(p.escrow_paid) if p.escrow_paid else None,
            "fees_paid": float(p.fees_paid) if p.fees_paid else None,
            "total_payment": float(p.total_payment) if p.total_payment else None,
            "principal_balance_after": float(p.principal_balance_after) if p.principal_balance_after else None,
            "payment_status": p.payment_status,
            "days_late": p.days_late
        }
        for p in payment_history
    ]
    
    # Convert mortgage to dict and add payment history
    mortgage_dict = {
        **mortgage.__dict__,
        "payment_history": payment_history_dicts
    }
    
    return mortgage_dict


@router.put("/{mortgage_id}", response_model=MortgageStatementResponse)
def update_mortgage(
    mortgage_id: int = Path(..., description="Mortgage Statement ID"),
    db: Session = Depends(get_db)
):
    """
    Update mortgage statement data after review
    
    Note: This is a placeholder - implement with proper update schema
    """
    mortgage = db.query(MortgageStatementData).filter(
        MortgageStatementData.id == mortgage_id
    ).first()
    
    if not mortgage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mortgage statement {mortgage_id} not found"
        )
    
    # TODO: Implement update logic with proper request body
    mortgage.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mortgage)
    
    return mortgage


@router.delete("/{mortgage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mortgage(
    mortgage_id: int = Path(..., description="Mortgage Statement ID"),
    db: Session = Depends(get_db)
):
    """
    Delete a mortgage statement
    """
    mortgage = db.query(MortgageStatementData).filter(
        MortgageStatementData.id == mortgage_id
    ).first()
    
    if not mortgage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mortgage statement {mortgage_id} not found"
        )
    
    db.delete(mortgage)
    db.commit()
    
    return None


@router.get("/properties/{property_id}/dscr-history", response_model=DSCRHistoryResponse)
def get_dscr_history(
    property_id: int = Path(..., description="Property ID"),
    limit: int = Query(12, ge=1, le=60, description="Number of periods to return"),
    db: Session = Depends(get_db)
):
    """
    Get DSCR history over time for a property
    """
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )
    
    dscr_service = DSCRMonitoringService(db)
    history = dscr_service.get_dscr_history(property_id, limit)
    
    return {
        "property_id": property_id,
        "property_code": property_obj.property_code,
        "history": history
    }


@router.get("/properties/{property_id}/dscr/latest-complete")
def get_latest_complete_dscr(
    property_id: int = Path(..., description="Property ID"),
    year: Optional[int] = Query(None, description="Optional year filter (e.g., 2025)"),
    db: Session = Depends(get_db)
):
    """
    Get DSCR for the latest COMPLETE period (has both income and mortgage data).

    This endpoint ensures DSCR is calculated only when complete data is available,
    preventing N/A or NULL values when the latest period by date is incomplete.

    Returns:
        - period: The latest complete period information
        - dscr: The DSCR value for that period
        - noi: Net Operating Income
        - debt_service: Annual debt service
        - status: DSCR health status (healthy/warning/critical)
    """
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )

    # Get latest complete period using MetricsService
    metrics_service = MetricsService(db)
    latest_complete_period = metrics_service.get_latest_complete_period(property_id, year)

    if not latest_complete_period:
        return {
            "property_id": property_id,
            "property_code": property_obj.property_code,
            "period": None,
            "dscr": None,
            "noi": None,
            "debt_service": None,
            "status": "no_data",
            "error": "No complete financial data available" + (f" for year {year}" if year else "")
        }

    # Get financial metrics for this period
    metrics = db.query(FinancialMetrics).filter(
        FinancialMetrics.property_id == property_id,
        FinancialMetrics.period_id == latest_complete_period.id
    ).first()

    if not metrics:
        # Calculate metrics if they don't exist
        metrics = metrics_service.calculate_all_metrics(property_id, latest_complete_period.id)

    # Extract DSCR and related values
    dscr = float(metrics.dscr) if metrics.dscr else None
    noi = float(metrics.net_operating_income) if metrics.net_operating_income else None
    debt_service = float(metrics.total_annual_debt_service) if metrics.total_annual_debt_service else None

    # Determine status
    if dscr is None:
        status = "unknown"
    elif dscr >= 1.25:
        status = "healthy"
    elif dscr >= 1.10:
        status = "warning"
    else:
        status = "critical"

    return {
        "property_id": property_id,
        "property_code": property_obj.property_code,
        "period": {
            "period_id": latest_complete_period.id,
            "period_year": latest_complete_period.period_year,
            "period_month": latest_complete_period.period_month,
            "period_label": f"{latest_complete_period.period_year}-{latest_complete_period.period_month:02d}",
            "period_start_date": latest_complete_period.period_start_date.isoformat() if latest_complete_period.period_start_date else None,
            "period_end_date": latest_complete_period.period_end_date.isoformat() if latest_complete_period.period_end_date else None
        },
        "dscr": dscr,
        "noi": noi,
        "debt_service": debt_service,
        "status": status
    }


@router.get("/properties/{property_id}/ltv-history", response_model=LTVHistoryResponse)
def get_ltv_history(
    property_id: int = Path(..., description="Property ID"),
    limit: int = Query(12, ge=1, le=60, description="Number of periods to return"),
    db: Session = Depends(get_db)
):
    """
    Get LTV history over time for a property
    """
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )
    
    # Get periods
    periods = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property_id
    ).order_by(desc(FinancialPeriod.period_end_date)).limit(limit).all()
    
    history = []
    for period in reversed(periods):
        # Get mortgage debt
        total_mortgage_debt = db.query(
            func.sum(MortgageStatementData.principal_balance)
        ).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period.id
        ).scalar() or Decimal('0')
        
        # Get property value from balance sheet
        from app.models.balance_sheet_data import BalanceSheetData
        property_value = db.query(BalanceSheetData.amount).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period.id,
            BalanceSheetData.account_code == '1999-0000'  # Total Property & Equipment
        ).first()
        
        ltv = None
        if property_value and property_value[0] and property_value[0] > 0:
            ltv = float(total_mortgage_debt / property_value[0])
        
        history.append({
            "period": period.period_end_date.isoformat() if period.period_end_date else None,
            "period_id": period.id,
            "ltv": ltv,
            "mortgage_debt": float(total_mortgage_debt),
            "property_value": float(property_value[0]) if property_value and property_value[0] else None
        })
    
    return {
        "property_id": property_id,
        "property_code": property_obj.property_code,
        "history": history
    }


@router.get("/properties/{property_id}/periods/{period_id}/debt-summary", response_model=DebtSummaryResponse)
def get_debt_summary(
    property_id: int = Path(..., description="Property ID"),
    period_id: int = Path(..., description="Financial Period ID"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive debt summary for a property/period
    """
    # Get all mortgages
    mortgages = db.query(MortgageStatementData).filter(
        MortgageStatementData.property_id == property_id,
        MortgageStatementData.period_id == period_id
    ).all()
    
    # Get metrics
    metrics = db.query(FinancialMetrics).filter(
        FinancialMetrics.property_id == property_id,
        FinancialMetrics.period_id == period_id
    ).first()
    
    return {
        "property_id": property_id,
        "period_id": period_id,
        "total_mortgage_debt": float(metrics.total_mortgage_debt) if metrics and metrics.total_mortgage_debt else None,
        "weighted_avg_interest_rate": float(metrics.weighted_avg_interest_rate) if metrics and metrics.weighted_avg_interest_rate else None,
        "total_monthly_debt_service": float(metrics.total_monthly_debt_service) if metrics and metrics.total_monthly_debt_service else None,
        "total_annual_debt_service": float(metrics.total_annual_debt_service) if metrics and metrics.total_annual_debt_service else None,
        "dscr": float(metrics.dscr) if metrics and metrics.dscr else None,
        "interest_coverage_ratio": float(metrics.interest_coverage_ratio) if metrics and metrics.interest_coverage_ratio else None,
        "debt_yield": float(metrics.debt_yield) if metrics and metrics.debt_yield else None,
        "break_even_occupancy": float(metrics.break_even_occupancy) if metrics and metrics.break_even_occupancy else None,
        "mortgage_count": len(mortgages),
        "mortgages": mortgages
    }


@router.get("/covenant-monitoring", response_model=List[CovenantMonitoringResponse])
def get_covenant_monitoring(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    db: Session = Depends(get_db)
):
    """
    Get covenant compliance dashboard for all properties or a specific property
    """
    dscr_service = DSCRMonitoringService(db)
    
    if property_id:
        properties = db.query(Property).filter(Property.id == property_id).all()
    else:
        properties = db.query(Property).filter(Property.status == 'active').all()
    
    results = []
    for prop in properties:
        covenant_status = dscr_service.get_covenant_status(prop.id)
        
        # Get LTV
        latest_period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == prop.id
        ).order_by(desc(FinancialPeriod.period_end_date)).first()
        
        ltv = None
        ltv_status = "unknown"
        if latest_period:
            metrics = db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == prop.id,
                FinancialMetrics.period_id == latest_period.id
            ).first()
            if metrics and metrics.ltv_ratio:
                ltv = float(metrics.ltv_ratio)
                if ltv <= 0.80:
                    ltv_status = "compliant"
                elif ltv <= 0.90:
                    ltv_status = "warning"
                else:
                    ltv_status = "breach"
        
        dscr = covenant_status.get("dscr")
        dscr_status = covenant_status.get("status", "unknown")
        covenant_compliant = (
            covenant_status.get("covenant_compliant", False) and
            ltv_status in ["compliant", "warning"]
        )
        
        results.append({
            "property_id": prop.id,
            "property_code": prop.property_code,
            "dscr": dscr,
            "dscr_status": dscr_status,
            "ltv": ltv,
            "ltv_status": ltv_status,
            "covenant_compliant": covenant_compliant,
            "active_alerts": covenant_status.get("active_alerts", 0),
            "active_locks": covenant_status.get("active_locks", 0)
        })
    
    return results


@router.get("/maturity-calendar", response_model=MaturityCalendarResponse)
def get_maturity_calendar(
    months_ahead: int = Query(24, ge=1, le=60, description="Number of months ahead to look"),
    db: Session = Depends(get_db)
):
    """
    Get loan maturity calendar (upcoming maturities)
    """
    from datetime import timedelta
    
    cutoff_date = date.today() + timedelta(days=months_ahead * 30)
    
    # Get mortgages with maturity dates in the next N months
    mortgages = db.query(MortgageStatementData).join(
        Property, MortgageStatementData.property_id == Property.id
    ).filter(
        MortgageStatementData.maturity_date.isnot(None),
        MortgageStatementData.maturity_date >= date.today(),
        MortgageStatementData.maturity_date <= cutoff_date
    ).order_by(MortgageStatementData.maturity_date).all()
    
    upcoming_maturities = []
    for mortgage in mortgages:
        property_obj = db.query(Property).filter(Property.id == mortgage.property_id).first()
        days_until = (mortgage.maturity_date - date.today()).days if mortgage.maturity_date else None
        
        upcoming_maturities.append({
            "mortgage_id": mortgage.id,
            "property_id": mortgage.property_id,
            "property_code": property_obj.property_code if property_obj else None,
            "loan_number": mortgage.loan_number,
            "maturity_date": mortgage.maturity_date.isoformat() if mortgage.maturity_date else None,
            "days_until_maturity": days_until,
            "principal_balance": float(mortgage.principal_balance) if mortgage.principal_balance else None,
            "interest_rate": float(mortgage.interest_rate) if mortgage.interest_rate else None
        })
    
    return {
        "upcoming_maturities": upcoming_maturities,
        "total_upcoming": len(upcoming_maturities)
    }


