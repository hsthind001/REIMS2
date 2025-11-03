"""
Financial Metrics API - Query calculated KPIs and performance metrics
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.services.metrics_service import MetricsService
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


router = APIRouter()


# Response Models

class FinancialMetricsResponse(BaseModel):
    """Complete financial metrics for a property/period"""
    property_id: int
    property_code: str
    period_id: int
    period_year: int
    period_month: int
    
    # Balance Sheet Metrics
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity_ratio: Optional[float] = None
    
    # Income Statement Metrics
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    net_operating_income: Optional[float] = None
    net_income: Optional[float] = None
    operating_margin: Optional[float] = None
    profit_margin: Optional[float] = None
    
    # Cash Flow Metrics
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    net_cash_flow: Optional[float] = None
    beginning_cash_balance: Optional[float] = None
    ending_cash_balance: Optional[float] = None
    
    # Rent Roll Metrics
    total_units: Optional[int] = None
    occupied_units: Optional[int] = None
    vacant_units: Optional[int] = None
    occupancy_rate: Optional[float] = None
    total_leasable_sqft: Optional[float] = None
    occupied_sqft: Optional[float] = None
    total_monthly_rent: Optional[float] = None
    total_annual_rent: Optional[float] = None
    avg_rent_per_sqft: Optional[float] = None
    
    # Performance Metrics
    noi_per_sqft: Optional[float] = None
    revenue_per_sqft: Optional[float] = None
    expense_ratio: Optional[float] = None
    
    # Metadata
    calculated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "property_id": 1,
                "property_code": "WEND001",
                "period_id": 45,
                "period_year": 2024,
                "period_month": 12,
                "total_assets": 22939865.40,
                "total_liabilities": 21769610.72,
                "total_equity": 1170254.68,
                "current_ratio": 1.05,
                "debt_to_equity_ratio": 18.60,
                "total_revenue": 3179456.89,
                "net_operating_income": 1860030.71,
                "net_income": -571883.75,
                "operating_margin": 58.52,
                "profit_margin": -17.99,
                "occupancy_rate": 95.0,
                "total_units": 20
            }
        }


class MetricsRecalculateResponse(BaseModel):
    """Response after metrics recalculation"""
    property_code: str
    period_year: int
    period_month: int
    success: bool
    message: str
    metrics_calculated: int


class MetricsSummaryItem(BaseModel):
    """Summary metrics for dashboard"""
    property_code: str
    property_name: str
    period_year: int
    period_month: int
    total_assets: Optional[float] = None
    total_revenue: Optional[float] = None
    net_income: Optional[float] = None
    occupancy_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


# Endpoints

@router.get("/metrics/{property_code}/{year}/{month}", response_model=FinancialMetricsResponse)
async def get_financial_metrics(
    property_code: str = Path(..., description="Property code"),
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    db: Session = Depends(get_db)
):
    """
    Get all calculated financial metrics for a property/period
    
    Returns all 35 metrics including:
    - Balance sheet ratios
    - Income statement margins  
    - Cash flow summaries
    - Rent roll occupancy
    - Performance metrics
    
    Metrics are automatically calculated after document extraction
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_code}' not found"
            )
        
        # Get period
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_obj.id,
            FinancialPeriod.period_year == year,
            FinancialPeriod.period_month == month
        ).first()
        
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Period {year}-{month:02d} not found for property {property_code}"
            )
        
        # Get metrics
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_obj.id,
            FinancialMetrics.period_id == period.id
        ).first()
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metrics not calculated for {property_code} {year}-{month:02d}. Upload and extract documents first."
            )
        
        # Build response
        response = FinancialMetricsResponse(
            property_id=property_obj.id,
            property_code=property_code,
            period_id=period.id,
            period_year=year,
            period_month=month,
            total_assets=float(metrics.total_assets) if metrics.total_assets else None,
            total_liabilities=float(metrics.total_liabilities) if metrics.total_liabilities else None,
            total_equity=float(metrics.total_equity) if metrics.total_equity else None,
            current_ratio=float(metrics.current_ratio) if metrics.current_ratio else None,
            debt_to_equity_ratio=float(metrics.debt_to_equity_ratio) if metrics.debt_to_equity_ratio else None,
            total_revenue=float(metrics.total_revenue) if metrics.total_revenue else None,
            total_expenses=float(metrics.total_expenses) if metrics.total_expenses else None,
            net_operating_income=float(metrics.net_operating_income) if metrics.net_operating_income else None,
            net_income=float(metrics.net_income) if metrics.net_income else None,
            operating_margin=float(metrics.operating_margin) if metrics.operating_margin else None,
            profit_margin=float(metrics.profit_margin) if metrics.profit_margin else None,
            operating_cash_flow=float(metrics.operating_cash_flow) if metrics.operating_cash_flow else None,
            investing_cash_flow=float(metrics.investing_cash_flow) if metrics.investing_cash_flow else None,
            financing_cash_flow=float(metrics.financing_cash_flow) if metrics.financing_cash_flow else None,
            net_cash_flow=float(metrics.net_cash_flow) if metrics.net_cash_flow else None,
            beginning_cash_balance=float(metrics.beginning_cash_balance) if metrics.beginning_cash_balance else None,
            ending_cash_balance=float(metrics.ending_cash_balance) if metrics.ending_cash_balance else None,
            total_units=metrics.total_units,
            occupied_units=metrics.occupied_units,
            vacant_units=metrics.vacant_units,
            occupancy_rate=float(metrics.occupancy_rate) if metrics.occupancy_rate else None,
            total_leasable_sqft=float(metrics.total_leasable_sqft) if metrics.total_leasable_sqft else None,
            occupied_sqft=float(metrics.occupied_sqft) if metrics.occupied_sqft else None,
            total_monthly_rent=float(metrics.total_monthly_rent) if metrics.total_monthly_rent else None,
            total_annual_rent=float(metrics.total_annual_rent) if metrics.total_annual_rent else None,
            avg_rent_per_sqft=float(metrics.avg_rent_per_sqft) if metrics.avg_rent_per_sqft else None,
            noi_per_sqft=float(metrics.noi_per_sqft) if metrics.noi_per_sqft else None,
            revenue_per_sqft=float(metrics.revenue_per_sqft) if metrics.revenue_per_sqft else None,
            expense_ratio=float(metrics.expense_ratio) if metrics.expense_ratio else None,
            calculated_at=metrics.calculated_at
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.post("/metrics/{property_code}/{year}/{month}/recalculate", response_model=MetricsRecalculateResponse)
async def recalculate_metrics(
    property_code: str = Path(..., description="Property code"),
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger metrics recalculation
    
    Useful for:
    - After manual data corrections
    - After bulk data imports
    - Testing metrics calculations
    
    Returns:
    - Success status
    - Number of metrics calculated
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_code}' not found"
            )
        
        # Get period
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_obj.id,
            FinancialPeriod.period_year == year,
            FinancialPeriod.period_month == month
        ).first()
        
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Period {year}-{month:02d} not found for property {property_code}"
            )
        
        # Recalculate metrics
        metrics_service = MetricsService(db)
        metrics = metrics_service.calculate_all_metrics(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        # Count non-null metrics
        metrics_calculated = sum(
            1 for field in FinancialMetricsResponse.model_fields.keys()
            if getattr(metrics, field, None) is not None
        )
        
        return MetricsRecalculateResponse(
            property_code=property_code,
            period_year=year,
            period_month=month,
            success=True,
            message="Metrics recalculated successfully",
            metrics_calculated=metrics_calculated
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate metrics: {str(e)}"
        )


@router.get("/metrics/summary", response_model=List[MetricsSummaryItem])
async def get_metrics_summary(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get metrics summary for all properties
    
    Dashboard overview showing key metrics for all properties
    Returns most recent period for each property
    
    Pagination:
    - skip: Number of records to skip
    - limit: Maximum records to return (max 500)
    """
    try:
        # Get latest metrics for each property
        query = db.query(
            FinancialMetrics,
            Property.property_code,
            Property.property_name,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).order_by(
            Property.property_code,
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).offset(skip).limit(limit)
        
        results = query.all()
        
        summary_items = []
        for metrics, prop_code, prop_name, year, month in results:
            summary_items.append(MetricsSummaryItem(
                property_code=prop_code,
                property_name=prop_name,
                period_year=year,
                period_month=month,
                total_assets=float(metrics.total_assets) if metrics.total_assets else None,
                total_revenue=float(metrics.total_revenue) if metrics.total_revenue else None,
                net_income=float(metrics.net_income) if metrics.net_income else None,
                occupancy_rate=float(metrics.occupancy_rate) if metrics.occupancy_rate else None
            ))
        
        return summary_items
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics summary: {str(e)}"
        )


@router.get("/metrics/{property_code}/trends", response_model=List[FinancialMetricsResponse])
async def get_metrics_trends(
    property_code: str,
    start_year: Optional[int] = Query(None, ge=2000, le=2100),
    end_year: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db)
):
    """
    Get metrics over time for trend analysis
    
    Returns metrics for multiple periods for a property
    Useful for dashboards and charts
    
    Query params:
    - start_year: Start year (optional)
    - end_year: End year (optional)
    
    If not specified, returns all available periods
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_code}' not found"
            )
        
        # Build query
        query = db.query(
            FinancialMetrics,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).filter(
            FinancialMetrics.property_id == property_obj.id
        )
        
        # Apply year filters
        if start_year:
            query = query.filter(FinancialPeriod.period_year >= start_year)
        if end_year:
            query = query.filter(FinancialPeriod.period_year <= end_year)
        
        # Order by period
        query = query.order_by(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        )
        
        results = query.all()
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No metrics found for property {property_code}"
            )
        
        # Build response
        trends = []
        for metrics, year, month in results:
            trends.append(FinancialMetricsResponse(
                property_id=property_obj.id,
                property_code=property_code,
                period_id=metrics.period_id,
                period_year=year,
                period_month=month,
                total_assets=float(metrics.total_assets) if metrics.total_assets else None,
                total_liabilities=float(metrics.total_liabilities) if metrics.total_liabilities else None,
                total_equity=float(metrics.total_equity) if metrics.total_equity else None,
                current_ratio=float(metrics.current_ratio) if metrics.current_ratio else None,
                debt_to_equity_ratio=float(metrics.debt_to_equity_ratio) if metrics.debt_to_equity_ratio else None,
                total_revenue=float(metrics.total_revenue) if metrics.total_revenue else None,
                total_expenses=float(metrics.total_expenses) if metrics.total_expenses else None,
                net_operating_income=float(metrics.net_operating_income) if metrics.net_operating_income else None,
                net_income=float(metrics.net_income) if metrics.net_income else None,
                operating_margin=float(metrics.operating_margin) if metrics.operating_margin else None,
                profit_margin=float(metrics.profit_margin) if metrics.profit_margin else None,
                operating_cash_flow=float(metrics.operating_cash_flow) if metrics.operating_cash_flow else None,
                investing_cash_flow=float(metrics.investing_cash_flow) if metrics.investing_cash_flow else None,
                financing_cash_flow=float(metrics.financing_cash_flow) if metrics.financing_cash_flow else None,
                net_cash_flow=float(metrics.net_cash_flow) if metrics.net_cash_flow else None,
                total_units=metrics.total_units,
                occupied_units=metrics.occupied_units,
                vacant_units=metrics.vacant_units,
                occupancy_rate=float(metrics.occupancy_rate) if metrics.occupancy_rate else None,
                total_leasable_sqft=float(metrics.total_leasable_sqft) if metrics.total_leasable_sqft else None,
                occupied_sqft=float(metrics.occupied_sqft) if metrics.occupied_sqft else None,
                total_monthly_rent=float(metrics.total_monthly_rent) if metrics.total_monthly_rent else None,
                total_annual_rent=float(metrics.total_annual_rent) if metrics.total_annual_rent else None,
                avg_rent_per_sqft=float(metrics.avg_rent_per_sqft) if metrics.avg_rent_per_sqft else None,
                noi_per_sqft=float(metrics.noi_per_sqft) if metrics.noi_per_sqft else None,
                revenue_per_sqft=float(metrics.revenue_per_sqft) if metrics.revenue_per_sqft else None,
                expense_ratio=float(metrics.expense_ratio) if metrics.expense_ratio else None,
                calculated_at=metrics.calculated_at
            ))
        
        return trends
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics trends: {str(e)}"
        )

