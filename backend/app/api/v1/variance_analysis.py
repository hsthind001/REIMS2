"""
Variance Analysis API Endpoints

Budget vs Actual and Forecast vs Actual variance analysis
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from datetime import datetime

from app.db.database import get_db
from app.services.variance_analysis_service import VarianceAnalysisService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.budget import Budget, BudgetStatus
from app.models.forecast import Forecast
from app.models.financial_metrics import FinancialMetrics

router = APIRouter(prefix="/variance-analysis", tags=["variance_analysis"])
logger = logging.getLogger(__name__)


class DataStatusResponse(BaseModel):
    """Reconciliation data status for a property/period (metrics, budget, forecast)."""
    property_id: int
    period_id: int
    has_metrics: bool
    approved_budget_count: int
    draft_budget_count: int
    approved_forecast_count: int
    draft_forecast_count: int


@router.get("/")
def get_variance_analysis(
    property_id: int,
    period_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get variance analysis summary.
    
    If period_id is provided, returns comprehensive report for that period.
    If not, attempts to find the latest closed period.
    """
    try:
        # If no period specified, find the latest closed period for this property
        if not period_id:
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.is_closed == True
            ).order_by(FinancialPeriod.period_end_date.desc()).first()
            
            if not period:
                # If no closed period, try latest open period
                period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property_id
                ).order_by(FinancialPeriod.period_end_date.desc()).first()
                
            if period:
                period_id = period.id
            else:
                 # No periods found at all
                return {
                    "success": False,
                    "error": "No financial periods found for this property",
                    "data": None
                }
        
        service = VarianceAnalysisService(db)
        result = service.get_variance_report(
            property_id=property_id,
            financial_period_id=period_id,
            include_budget=True,
            include_forecast=True
        )
        return result

    except Exception as e:
        logger.error(f"Error fetching variance analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BudgetVarianceRequest(BaseModel):
    property_id: int
    financial_period_id: int
    budget_id: Optional[int] = None


class ForecastVarianceRequest(BaseModel):
    property_id: int
    financial_period_id: int
    forecast_id: Optional[int] = None


class VarianceReportRequest(BaseModel):
    property_id: int
    financial_period_id: int
    include_budget: bool = True
    include_forecast: bool = True


@router.post("/budget")
def analyze_budget_variance(
    request: BudgetVarianceRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze variance between actual results and budget

    Compares actual financial results against budgeted amounts at the account level.

    **Variance Calculation:**
    - Variance Amount = Actual - Budget
    - Variance % = (Variance Amount / Budget) × 100

    **Tolerance Thresholds:**
    - Default: ±10% (configurable per account)
    - WARNING: 10-25% variance
    - CRITICAL: 25-50% variance
    - URGENT: >50% variance

    **Favorable vs Unfavorable:**
    - Revenue (4xxxx): Actual > Budget = Favorable
    - Expenses (5xxxx, 6xxxx): Actual < Budget = Favorable

    **Returns:**
    - Account-level variance details
    - Flagged accounts exceeding tolerance
    - Summary totals
    - Alerts created for critical variances
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == request.financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.analyze_budget_variance(
            property_id=request.property_id,
            financial_period_id=request.financial_period_id,
            budget_id=request.budget_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Budget variance analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast")
def analyze_forecast_variance(
    request: ForecastVarianceRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze variance between actual results and forecast

    Compares actual financial results against forecasted amounts.

    **Differences from Budget Variance:**
    - More lenient tolerance (default 15% vs 10%)
    - Tracks forecast type (original, reforecast, rolling)
    - Includes forecast date for reforecast tracking

    **Use Cases:**
    - Reforecast accuracy analysis
    - Rolling forecast validation
    - Mid-year performance tracking
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == request.financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.analyze_forecast_variance(
            property_id=request.property_id,
            financial_period_id=request.financial_period_id,
            forecast_id=request.forecast_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Forecast variance analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/periods/{period_id}/budget")
def get_budget_variance(
    property_id: int,
    period_id: int,
    budget_id: Optional[int] = Query(None, description="Specific budget ID"),
    db: Session = Depends(get_db)
):
    """
    Get budget variance analysis (GET endpoint)

    Convenience GET endpoint for budget variance analysis.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.analyze_budget_variance(
            property_id=property_id,
            financial_period_id=period_id,
            budget_id=budget_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Budget variance analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/periods/{period_id}/forecast")
def get_forecast_variance(
    property_id: int,
    period_id: int,
    forecast_id: Optional[int] = Query(None, description="Specific forecast ID"),
    db: Session = Depends(get_db)
):
    """
    Get forecast variance analysis (GET endpoint)

    Convenience GET endpoint for forecast variance analysis.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.analyze_forecast_variance(
            property_id=property_id,
            financial_period_id=period_id,
            forecast_id=forecast_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Forecast variance analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/budgets/{budget_id}/approve")
def approve_budget(
    budget_id: int,
    approved_by: Optional[int] = Query(None, description="User ID approving (optional)"),
    db: Session = Depends(get_db)
):
    """
    Approve a budget so AUDIT-51 and TREND-3 use it in reconciliation.

    Sets status to APPROVED and optionally records approved_by/approved_at.
    Only DRAFT (or REVISED) budgets can be approved.
    """
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REVISED):
        raise HTTPException(
            status_code=400,
            detail=f"Budget status is {budget.status.value}; only DRAFT or REVISED can be approved"
        )
    budget.status = BudgetStatus.APPROVED
    budget.approved_by = approved_by
    budget.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(budget)
    return {
        "success": True,
        "budget_id": budget_id,
        "status": budget.status.value,
        "approved_at": budget.approved_at.isoformat() if budget.approved_at else None,
    }


@router.put("/forecasts/{forecast_id}/approve")
def approve_forecast(
    forecast_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve a forecast so AUDIT-52 uses it in reconciliation.

    Sets status to APPROVED. Only DRAFT (or REVISED) forecasts can be approved.
    """
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    if forecast.status not in (BudgetStatus.DRAFT, BudgetStatus.REVISED):
        raise HTTPException(
            status_code=400,
            detail=f"Forecast status is {forecast.status.value}; only DRAFT or REVISED can be approved"
        )
    forecast.status = BudgetStatus.APPROVED
    db.commit()
    db.refresh(forecast)
    return {
        "success": True,
        "forecast_id": forecast_id,
        "status": forecast.status.value,
    }


class ApproveByPeriodRequest(BaseModel):
    """Request body for approve-by-period endpoints."""
    property_id: int
    financial_period_id: int
    approved_by: Optional[int] = None  # For budgets only


@router.post("/budgets/approve-by-period")
def approve_budgets_by_period(
    request: ApproveByPeriodRequest,
    db: Session = Depends(get_db)
):
    """
    Approve all DRAFT/REVISED budgets for a property and period.

    Convenience endpoint after bulk import: approve every budget row for the given
    property_id and financial_period_id so AUDIT-51 and TREND-3 use them.
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == request.financial_period_id,
        FinancialPeriod.property_id == request.property_id,
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found for this property")
    budgets = db.query(Budget).filter(
        Budget.property_id == request.property_id,
        Budget.financial_period_id == request.financial_period_id,
        Budget.status.in_([BudgetStatus.DRAFT, BudgetStatus.REVISED]),
    ).all()
    now = datetime.utcnow()
    for b in budgets:
        b.status = BudgetStatus.APPROVED
        b.approved_by = request.approved_by
        b.approved_at = now
    db.commit()
    return {
        "success": True,
        "property_id": request.property_id,
        "financial_period_id": request.financial_period_id,
        "approved_count": len(budgets),
        "budget_ids": [b.id for b in budgets],
    }


@router.post("/forecasts/approve-by-period")
def approve_forecasts_by_period(
    request: ApproveByPeriodRequest,
    db: Session = Depends(get_db)
):
    """
    Approve all DRAFT/REVISED forecasts for a property and period.

    Convenience endpoint after bulk import: approve every forecast row for the given
    property_id and financial_period_id so AUDIT-52 uses them.
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == request.financial_period_id,
        FinancialPeriod.property_id == request.property_id,
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found for this property")
    forecasts = db.query(Forecast).filter(
        Forecast.property_id == request.property_id,
        Forecast.financial_period_id == request.financial_period_id,
        Forecast.status.in_([BudgetStatus.DRAFT, BudgetStatus.REVISED]),
    ).all()
    for f in forecasts:
        f.status = BudgetStatus.APPROVED
    db.commit()
    return {
        "success": True,
        "property_id": request.property_id,
        "financial_period_id": request.financial_period_id,
        "approved_count": len(forecasts),
        "forecast_ids": [f.id for f in forecasts],
    }


@router.post("/comprehensive-report")
def get_comprehensive_variance_report(
    request: VarianceReportRequest,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive variance report

    Includes both budget and forecast variance analysis in single response.

    **Use Cases:**
    - Executive summary reports
    - Board presentations
    - Comprehensive performance review
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.get_variance_report(
            property_id=request.property_id,
            financial_period_id=request.financial_period_id,
            include_budget=request.include_budget,
            include_forecast=request.include_forecast
        )

        return result

    except Exception as e:
        logger.error(f"Comprehensive variance report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/periods/{period_id}/comprehensive")
def get_comprehensive_report(
    property_id: int,
    period_id: int,
    include_budget: bool = Query(default=True),
    include_forecast: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive variance report (GET endpoint)

    Returns both budget and forecast variance in single call.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.get_variance_report(
            property_id=property_id,
            financial_period_id=period_id,
            include_budget=include_budget,
            include_forecast=include_forecast
        )

        return result

    except Exception as e:
        logger.error(f"Comprehensive variance report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/trend")
def get_variance_trend(
    property_id: int,
    variance_type: str = Query(default="budget", regex="^(budget|forecast)$"),
    lookback_periods: int = Query(default=6, ge=2, le=24),
    db: Session = Depends(get_db)
):
    """
    Get variance trend over time

    Analyzes variance patterns across multiple periods to identify trends.

    **Parameters:**
    - variance_type: "budget" or "forecast"
    - lookback_periods: Number of historical periods (2-24)

    **Returns:**
    - Variance percentage by period
    - Flagged account count by period
    - Trend direction (improving/deteriorating)

    **Use Cases:**
    - Performance trend analysis
    - Budget/forecast accuracy tracking
    - Early warning of systemic issues
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.get_variance_trend(
            property_id=property_id,
            lookback_periods=lookback_periods,
            variance_type=variance_type
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Variance trend analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/periods/{period_id}/period-over-period")
def get_period_over_period_variance(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get period-over-period variance analysis

    Compares actual results from the selected period with actual results from the previous period.
    No budget or forecast comparison - purely actual vs previous actual.

    **Variance Calculation:**
    - Variance Amount = Current Period Actual - Previous Period Actual
    - Variance % = (Variance Amount / Previous Period Actual) × 100

    **Use Cases:**
    - Month-over-month performance tracking
    - Identifying trends in revenue and expenses
    - Period comparison without budget dependency

    **Returns:**
    - Account-level variance between periods
    - Previous and current period details
    - Summary totals and severity breakdown
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VarianceAnalysisService(db)

    try:
        result = service.analyze_period_over_period_variance(
            property_id=property_id,
            current_period_id=period_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Period-over-period variance analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/periods/{period_id}/data-status", response_model=DataStatusResponse)
def get_data_status(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db),
):
    """
    Get reconciliation data status for a property/period.

    Used by the UI to show checklist: metrics calculated, approved budget, approved forecast.
    """
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == period_id,
        FinancialPeriod.property_id == property_id,
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    has_metrics = (
        db.query(FinancialMetrics.id)
        .filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id,
        )
        .limit(1)
        .first()
        is not None
    )

    approved_budget_count = db.query(Budget).filter(
        Budget.property_id == property_id,
        Budget.financial_period_id == period_id,
        Budget.status == BudgetStatus.APPROVED,
    ).count()
    draft_budget_count = db.query(Budget).filter(
        Budget.property_id == property_id,
        Budget.financial_period_id == period_id,
        Budget.status.in_([BudgetStatus.DRAFT, BudgetStatus.REVISED]),
    ).count()

    approved_forecast_count = db.query(Forecast).filter(
        Forecast.property_id == property_id,
        Forecast.financial_period_id == period_id,
        Forecast.status == BudgetStatus.APPROVED,
    ).count()
    draft_forecast_count = db.query(Forecast).filter(
        Forecast.property_id == property_id,
        Forecast.financial_period_id == period_id,
        Forecast.status.in_([BudgetStatus.DRAFT, BudgetStatus.REVISED]),
    ).count()

    return DataStatusResponse(
        property_id=property_id,
        period_id=period_id,
        has_metrics=has_metrics,
        approved_budget_count=approved_budget_count,
        draft_budget_count=draft_budget_count,
        approved_forecast_count=approved_forecast_count,
        draft_forecast_count=draft_forecast_count,
    )


class BudgetLineResponse(BaseModel):
    id: int
    account_code: str
    account_name: Optional[str]
    budgeted_amount: float
    status: str

    class Config:
        from_attributes = True


class ForecastLineResponse(BaseModel):
    id: int
    account_code: str
    account_name: Optional[str]
    forecasted_amount: float
    status: str

    class Config:
        from_attributes = True


class BudgetLineUpdate(BaseModel):
    budgeted_amount: Optional[float] = None


class ForecastLineUpdate(BaseModel):
    forecasted_amount: Optional[float] = None


@router.get("/properties/{property_id}/periods/{period_id}/budgets", response_model=List[BudgetLineResponse])
def list_budgets_for_period(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db),
):
    """List budget line items for a property/period (for display and inline edit)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    rows = (
        db.query(Budget)
        .filter(
            Budget.property_id == property_id,
            Budget.financial_period_id == period_id,
        )
        .order_by(Budget.account_code)
        .all()
    )
    return [
        BudgetLineResponse(
            id=b.id,
            account_code=b.account_code,
            account_name=b.account_name,
            budgeted_amount=float(b.budgeted_amount or 0),
            status=b.status.value if b.status else "DRAFT",
        )
        for b in rows
    ]


@router.get("/properties/{property_id}/periods/{period_id}/forecasts", response_model=List[ForecastLineResponse])
def list_forecasts_for_period(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db),
):
    """List forecast line items for a property/period (for display and inline edit)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    rows = (
        db.query(Forecast)
        .filter(
            Forecast.property_id == property_id,
            Forecast.financial_period_id == period_id,
        )
        .order_by(Forecast.account_code)
        .all()
    )
    return [
        ForecastLineResponse(
            id=f.id,
            account_code=f.account_code,
            account_name=f.account_name,
            forecasted_amount=float(f.forecasted_amount or 0),
            status=f.status.value if f.status else "DRAFT",
        )
        for f in rows
    ]


@router.patch("/budgets/{budget_id}", response_model=BudgetLineResponse)
def update_budget_line(
    budget_id: int,
    body: BudgetLineUpdate,
    db: Session = Depends(get_db),
):
    """Update a single budget line (e.g. budgeted_amount). Only DRAFT/REVISED can be edited."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REVISED):
        raise HTTPException(
            status_code=400,
            detail=f"Only DRAFT or REVISED budgets can be edited (current: {budget.status.value})",
        )
    if body.budgeted_amount is not None:
        budget.budgeted_amount = body.budgeted_amount
    db.commit()
    db.refresh(budget)
    return BudgetLineResponse(
        id=budget.id,
        account_code=budget.account_code,
        account_name=budget.account_name,
        budgeted_amount=float(budget.budgeted_amount or 0),
        status=budget.status.value if budget.status else "DRAFT",
    )


@router.patch("/forecasts/{forecast_id}", response_model=ForecastLineResponse)
def update_forecast_line(
    forecast_id: int,
    body: ForecastLineUpdate,
    db: Session = Depends(get_db),
):
    """Update a single forecast line (e.g. forecasted_amount). Only DRAFT/REVISED can be edited."""
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    if forecast.status not in (BudgetStatus.DRAFT, BudgetStatus.REVISED):
        raise HTTPException(
            status_code=400,
            detail=f"Only DRAFT or REVISED forecasts can be edited (current: {forecast.status.value})",
        )
    if body.forecasted_amount is not None:
        forecast.forecasted_amount = body.forecasted_amount
    db.commit()
    db.refresh(forecast)
    return ForecastLineResponse(
        id=forecast.id,
        account_code=forecast.account_code,
        account_name=forecast.account_name,
        forecasted_amount=float(forecast.forecasted_amount or 0),
        status=forecast.status.value if forecast.status else "DRAFT",
    )


@router.get("/thresholds")
def get_variance_thresholds():
    """
    Get variance analysis thresholds and tolerances

    Returns default thresholds used for variance classification.
    """
    return {
        "success": True,
        "budget_defaults": {
            "tolerance_percentage": 10.0,
            "description": "Default tolerance for budget variances",
        },
        "forecast_defaults": {
            "tolerance_percentage": 15.0,
            "description": "Default tolerance for forecast variances (more lenient)",
        },
        "severity_thresholds": {
            "WARNING": {
                "min_percentage": 10.0,
                "max_percentage": 25.0,
                "description": "Variance between 10-25%",
            },
            "CRITICAL": {
                "min_percentage": 25.0,
                "max_percentage": 50.0,
                "description": "Variance between 25-50%",
            },
            "URGENT": {
                "min_percentage": 50.0,
                "max_percentage": None,
                "description": "Variance exceeds 50%",
            }
        },
        "favorable_variance_rules": {
            "revenue_accounts": {
                "prefix": "4xxxx",
                "rule": "Actual > Budget = Favorable",
                "description": "Higher revenue than expected is favorable"
            },
            "expense_accounts": {
                "prefix": "5xxxx, 6xxxx",
                "rule": "Actual < Budget = Favorable",
                "description": "Lower expenses than expected is favorable"
            }
        }
    }
