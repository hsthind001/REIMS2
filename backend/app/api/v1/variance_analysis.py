"""
Variance Analysis API Endpoints

Budget vs Actual and Forecast vs Actual variance analysis
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.database import get_db
from app.services.variance_analysis_service import VarianceAnalysisService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

router = APIRouter(prefix="/variance-analysis", tags=["variance_analysis"])
logger = logging.getLogger(__name__)


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
