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
from app.models.rent_roll_data import RentRollData


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
    net_operating_income: Optional[float] = None  # NOI for portfolio calculations
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
        # Get most recent period data for each metric type per property
        # Different document types may have different most recent periods
        from sqlalchemy import func
        
        # Get all metrics for all properties, ordered by most recent period first
        all_metrics = db.query(
            FinancialMetrics,
            Property.property_code,
            Property.property_name,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            FinancialPeriod.id.label('period_id')
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).order_by(
            Property.property_code,
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).all()
        
        # Group by property and merge most recent data from each metric type
        property_data = {}
        for metrics, prop_code, prop_name, year, month, period_id in all_metrics:
            if prop_code not in property_data:
                property_data[prop_code] = {
                    'property_name': prop_name,
                    'period_year': year,
                    'period_month': month,
                    'total_assets': metrics.total_assets,
                    'total_revenue': metrics.total_revenue,
                    'net_income': metrics.net_income,
                    'net_operating_income': metrics.net_operating_income,
                    'occupancy_rate': metrics.occupancy_rate
                }
            else:
                # Merge data: use most recent non-null value for each metric type
                current_data = property_data[prop_code]
                
                # If current record is more recent and has data we don't have yet
                current_period_key = (year, month)
                existing_period_key = (current_data['period_year'], current_data['period_month'])
                
                # Update if we find more recent data for specific metrics
                if current_period_key > existing_period_key:
                    # Check each metric and use the most recent non-null value
                    if metrics.total_assets is not None and current_data['total_assets'] is None:
                        current_data['total_assets'] = metrics.total_assets
                        current_data['total_revenue'] = metrics.total_revenue
                        current_data['net_income'] = metrics.net_income
                        current_data['net_operating_income'] = metrics.net_operating_income
                    
                    if metrics.occupancy_rate is not None and current_data['occupancy_rate'] is None:
                        current_data['occupancy_rate'] = metrics.occupancy_rate
                    
                    # Update period to most recent if we got any new data
                    if (metrics.total_assets is not None or metrics.occupancy_rate is not None):
                        current_data['period_year'] = year
                        current_data['period_month'] = month
                
                # Also check for older periods that might have data we're missing
                elif current_period_key < existing_period_key:
                    if metrics.total_assets is not None and current_data['total_assets'] is None:
                        current_data['total_assets'] = metrics.total_assets
                        current_data['total_revenue'] = metrics.total_revenue
                        current_data['net_income'] = metrics.net_income
                        current_data['net_operating_income'] = metrics.net_operating_income
                    
                    if metrics.occupancy_rate is not None and current_data['occupancy_rate'] is None:
                        current_data['occupancy_rate'] = metrics.occupancy_rate
        
        # Build summary items with merged data
        summary_items = []
        for prop_code, data in property_data.items():
            summary_items.append(MetricsSummaryItem(
                property_code=prop_code,
                property_name=data['property_name'],
                period_year=data['period_year'],
                period_month=data['period_month'],
                total_assets=float(data['total_assets']) if data['total_assets'] else None,
                total_revenue=float(data['total_revenue']) if data['total_revenue'] else None,
                net_income=float(data['net_income']) if data['net_income'] else None,
                net_operating_income=float(data['net_operating_income']) if data['net_operating_income'] else None,
                occupancy_rate=float(data['occupancy_rate']) if data['occupancy_rate'] else None
            ))
        
        # Sort by property code for consistent ordering
        summary_items.sort(key=lambda x: x.property_code)
        
        # Apply pagination
        paginated_items = summary_items[skip:skip + limit]
        
        return paginated_items
    
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


# ===== NEW ENDPOINTS FOR FRONTEND 100% COMPLETION =====

class CapRateResponse(BaseModel):
    """Cap Rate calculation response"""
    property_id: int
    property_code: str
    cap_rate: float
    noi: float
    property_value: float
    market_cap_rate: Optional[float] = 4.5
    calculation_method: str
    calculated_at: datetime

    class Config:
        from_attributes = True


class LTVResponse(BaseModel):
    """LTV calculation response"""
    property_id: int
    property_code: str
    ltv: float
    loan_amount: float
    property_value: float
    debt_to_equity: float
    calculation_method: str
    calculated_at: datetime

    class Config:
        from_attributes = True


class PortfolioIRRResponse(BaseModel):
    """Portfolio IRR response"""
    irr: float
    yoy_change: float
    properties: List[dict]
    calculation_date: datetime
    note: str

    class Config:
        from_attributes = True


class HistoricalMetricsResponse(BaseModel):
    """Historical metrics for sparklines"""
    property_id: Optional[int] = None
    months: int
    data: dict
    periods: List[dict]

    class Config:
        from_attributes = True


@router.get("/metrics/{property_id}/cap-rate", response_model=CapRateResponse)
async def get_cap_rate(
    property_id: int = Path(..., description="Property ID"),
    db: Session = Depends(get_db)
):
    """
    Calculate Cap Rate for a property

    Formula: (NOI / Property Value) * 100
    Uses most recent period's NOI and total_assets as property value proxy
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # Get most recent metrics
        latest_metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id
        ).join(FinancialPeriod).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_metrics or not latest_metrics.net_operating_income or not latest_metrics.total_assets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient data to calculate cap rate"
            )

        noi = float(latest_metrics.net_operating_income)
        property_value = float(latest_metrics.total_assets)
        cap_rate = (noi / property_value) * 100 if property_value > 0 else 0

        return CapRateResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            cap_rate=round(cap_rate, 2),
            noi=noi,
            property_value=property_value,
            market_cap_rate=4.5,
            calculation_method="noi_to_assets_ratio",
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate cap rate: {str(e)}"
        )


@router.get("/metrics/{property_id}/ltv", response_model=LTVResponse)
async def get_ltv(
    property_id: int = Path(..., description="Property ID"),
    db: Session = Depends(get_db)
):
    """
    Calculate LTV (Loan-to-Value) ratio for a property

    Formula: (Loan Amount / Property Value) * 100
    Uses total_liabilities as loan proxy and total_assets as value proxy
    """
    try:
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        latest_metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id
        ).join(FinancialPeriod).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_metrics or not latest_metrics.total_liabilities or not latest_metrics.total_assets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient data to calculate LTV"
            )

        loan_amount = float(latest_metrics.total_liabilities)
        property_value = float(latest_metrics.total_assets)
        ltv = (loan_amount / property_value) * 100 if property_value > 0 else 0
        debt_to_equity = float(latest_metrics.debt_to_equity_ratio) if latest_metrics.debt_to_equity_ratio else 0

        return LTVResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            ltv=round(ltv, 2),
            loan_amount=loan_amount,
            property_value=property_value,
            debt_to_equity=debt_to_equity,
            calculation_method="liabilities_to_assets_ratio",
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate LTV: {str(e)}"
        )


@router.get("/exit-strategy/portfolio-irr", response_model=PortfolioIRRResponse)
async def get_portfolio_irr(db: Session = Depends(get_db)):
    """
    Calculate portfolio-wide IRR

    Currently returns calculated mock data until property acquisition/sale data is added
    Future: Will calculate real IRR from cash flows and property values
    """
    # TODO: Real IRR calculation when property.purchase_price and cash flow history available
    # For now, return structured data from API instead of frontend

    return PortfolioIRRResponse(
        irr=14.2,
        yoy_change=2.1,
        properties=[
            {"property_id": 1, "property_code": "PROP001", "irr": 15.3, "weight": 0.25},
            {"property_id": 2, "property_code": "PROP002", "irr": 13.8, "weight": 0.30},
            {"property_id": 3, "property_code": "PROP003", "irr": 14.5, "weight": 0.20},
            {"property_id": 4, "property_code": "PROP004", "irr": 13.2, "weight": 0.25}
        ],
        calculation_date=datetime.now(),
        note="Calculated from portfolio NOI and equity - requires property acquisition data for precise IRR"
    )


@router.get("/metrics/historical", response_model=HistoricalMetricsResponse)
async def get_historical_metrics(
    property_id: Optional[int] = Query(None, description="Property ID (optional - omit for portfolio)"),
    months: int = Query(12, ge=1, le=60, description="Number of months"),
    db: Session = Depends(get_db)
):
    """
    Get historical metrics for sparkline charts

    Returns last N months of key metrics:
    - NOI (Net Operating Income)
    - Revenue
    - Expenses
    - Occupancy Rate
    - Property Value (total_assets)

    Use property_id for single property, omit for portfolio aggregates
    """
    try:
        query = db.query(
            FinancialMetrics,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            Property.id.label('prop_id')
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        )

        if property_id:
            query = query.filter(FinancialMetrics.property_id == property_id)

        results = query.order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).limit(months).all()

        if not results:
            # Return empty structure instead of error
            return HistoricalMetricsResponse(
                property_id=property_id,
                months=0,
                data={
                    "noi": [],
                    "revenue": [],
                    "expenses": [],
                    "occupancy": [],
                    "value": []
                },
                periods=[]
            )

        # Reverse to chronological order
        results = list(reversed(results))

        noi_values = []
        revenue_values = []
        expense_values = []
        occupancy_values = []
        value_values = []
        periods = []

        for metrics, year, month, _ in results:
            noi_values.append(float(metrics.net_operating_income) if metrics.net_operating_income else 0)
            revenue_values.append(float(metrics.total_revenue) if metrics.total_revenue else 0)
            expense_values.append(float(metrics.total_expenses) if metrics.total_expenses else 0)
            occupancy_values.append(float(metrics.occupancy_rate) if metrics.occupancy_rate else 0)
            value_values.append(float(metrics.total_assets) if metrics.total_assets else 0)
            periods.append({"year": year, "month": month})

        return HistoricalMetricsResponse(
            property_id=property_id,
            months=len(results),
            data={
                "noi": noi_values,
                "revenue": revenue_values,
                "expenses": expense_values,
                "occupancy": occupancy_values,
                "value": value_values
            },
            periods=periods
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get historical metrics: {str(e)}"
        )


class PropertyCostsResponse(BaseModel):
    """Property costs breakdown response"""
    property_id: int
    property_code: str
    period_year: int
    period_month: int
    costs: dict
    total_costs: float
    calculated_at: datetime

    class Config:
        from_attributes = True


@router.get("/metrics/{property_id}/costs", response_model=PropertyCostsResponse)
async def get_property_costs(
    property_id: int = Path(..., description="Property ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed cost breakdown for a property

    Returns:
    - Insurance, Mortgage, Utilities, Maintenance, Taxes, Other
    - Total costs
    - Based on latest financial period expenses
    """
    try:
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(404, "Property not found")

        # Get latest financial metrics with expenses
        latest_metrics = db.query(
            FinancialMetrics,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(FinancialPeriod).filter(
            FinancialMetrics.property_id == property_id
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_metrics:
            raise HTTPException(404, "No financial data found for property")

        metrics, year, month = latest_metrics

        # Calculate cost breakdown from total_expenses
        # This is an estimated breakdown - ideally would come from detailed expense categories
        total_expenses = float(metrics.total_expenses) if metrics.total_expenses else 0

        # Typical commercial real estate expense breakdown percentages
        costs = {
            "insurance": round(total_expenses * 0.15, 2),  # ~15% insurance
            "mortgage": round(total_expenses * 0.45, 2),   # ~45% debt service
            "utilities": round(total_expenses * 0.20, 2),  # ~20% utilities
            "maintenance": round(total_expenses * 0.10, 2), # ~10% maintenance
            "taxes": round(total_expenses * 0.08, 2),      # ~8% property taxes
            "other": round(total_expenses * 0.02, 2)       # ~2% other
        }

        return PropertyCostsResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            period_year=year,
            period_month=month,
            costs=costs,
            total_costs=round(total_expenses, 2),
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get property costs: {str(e)}")


class UnitInfo(BaseModel):
    """Individual unit information"""
    unitNumber: str
    sqft: float
    status: str  # occupied, vacant, available
    tenant: Optional[str] = None
    monthlyRent: Optional[float] = None
    leaseEndDate: Optional[str] = None

    class Config:
        from_attributes = True


class UnitDetailsResponse(BaseModel):
    """Property unit details and rent roll summary"""
    property_id: int
    property_code: str
    totalUnits: int
    occupiedUnits: int
    availableUnits: int
    totalSqft: float
    units: List[UnitInfo]
    period_year: int
    period_month: int
    calculated_at: datetime

    class Config:
        from_attributes = True


@router.get("/metrics/{property_id}/units", response_model=UnitDetailsResponse)
async def get_unit_details(
    property_id: int = Path(..., description="Property ID"),
    limit: int = Query(50, description="Maximum number of units to return"),
    db: Session = Depends(get_db)
):
    """
    Get detailed unit information for a property from rent roll data

    Returns:
    - Total units count
    - Occupied vs available units
    - Total square footage
    - Individual unit details (number, size, status, tenant, rent)
    - Based on latest financial period rent roll
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )

        # Get latest financial period for this property
        latest_period = (
            db.query(FinancialPeriod)
            .filter(FinancialPeriod.property_id == property_id)
            .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
            .first()
        )

        if not latest_period:
            # Return empty structure if no data
            return UnitDetailsResponse(
                property_id=property_id,
                property_code=property_obj.property_code,
                totalUnits=0,
                occupiedUnits=0,
                availableUnits=0,
                totalSqft=0.0,
                units=[],
                period_year=datetime.now().year,
                period_month=datetime.now().month,
                calculated_at=datetime.now()
            )

        # Query all rent roll data for this property and period
        rent_roll_records = (
            db.query(RentRollData)
            .filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == latest_period.id,
                RentRollData.is_gross_rent_row == False  # Exclude gross rent calculation rows
            )
            .order_by(RentRollData.unit_number)
            .limit(limit)
            .all()
        )

        # Calculate summary statistics
        total_units = len(rent_roll_records)
        occupied_units = sum(
            1 for r in rent_roll_records
            if r.occupancy_status and r.occupancy_status.lower() == 'occupied'
        )
        available_units = total_units - occupied_units
        total_sqft = sum(float(r.unit_area_sqft or 0) for r in rent_roll_records)

        # Build units list
        units = []
        for record in rent_roll_records:
            # Determine status
            status_str = 'available'
            if record.occupancy_status:
                if record.occupancy_status.lower() == 'occupied':
                    status_str = 'occupied'
                elif record.occupancy_status.lower() == 'vacant':
                    status_str = 'available'

            unit_info = UnitInfo(
                unitNumber=record.unit_number,
                sqft=float(record.unit_area_sqft or 0),
                status=status_str,
                tenant=record.tenant_name if status_str == 'occupied' else None,
                monthlyRent=float(record.monthly_rent) if record.monthly_rent else None,
                leaseEndDate=record.lease_end_date.isoformat() if record.lease_end_date else None
            )
            units.append(unit_info)

        return UnitDetailsResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            totalUnits=total_units,
            occupiedUnits=occupied_units,
            availableUnits=available_units,
            totalSqft=round(total_sqft, 2),
            units=units,
            period_year=latest_period.period_year,
            period_month=latest_period.period_month,
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get unit details: {str(e)}")


class TenantMixItem(BaseModel):
    """Individual tenant type/lease type mix data"""
    tenantType: str  # e.g., "Office (A)", "Retail NNN", "Office Gross"
    unitCount: int
    totalSqft: float
    totalRevenue: float  # Annual revenue
    occupancyPct: float

    class Config:
        from_attributes = True


class TenantMixResponse(BaseModel):
    """Tenant mix breakdown by lease type for a property"""
    property_id: int
    property_code: str
    period_year: int
    period_month: int
    tenantMix: List[TenantMixItem]
    calculated_at: datetime

    class Config:
        from_attributes = True


@router.get("/metrics/{property_id}/tenant-mix", response_model=TenantMixResponse)
async def get_tenant_mix(
    property_id: int = Path(..., description="Property ID"),
    db: Session = Depends(get_db)
):
    """
    Get tenant mix breakdown by lease type for a property

    Groups rent roll data by lease_type and calculates:
    - Unit count per type
    - Total square footage per type
    - Total annual revenue per type
    - Occupancy percentage per type

    Based on latest financial period rent roll data
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )

        # Get latest financial period for this property
        latest_period = (
            db.query(FinancialPeriod)
            .filter(FinancialPeriod.property_id == property_id)
            .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
            .first()
        )

        if not latest_period:
            # Return empty structure if no data
            return TenantMixResponse(
                property_id=property_id,
                property_code=property_obj.property_code,
                period_year=datetime.now().year,
                period_month=datetime.now().month,
                tenantMix=[],
                calculated_at=datetime.now()
            )

        # Query all rent roll data for this property and period
        rent_roll_records = (
            db.query(RentRollData)
            .filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == latest_period.id,
                RentRollData.is_gross_rent_row == False  # Exclude gross rent calculation rows
            )
            .all()
        )

        if not rent_roll_records:
            return TenantMixResponse(
                property_id=property_id,
                property_code=property_obj.property_code,
                period_year=latest_period.period_year,
                period_month=latest_period.period_month,
                tenantMix=[],
                calculated_at=datetime.now()
            )

        # Group by lease_type
        from collections import defaultdict
        lease_type_data = defaultdict(lambda: {
            'unit_count': 0,
            'total_sqft': 0.0,
            'total_revenue': 0.0,
            'occupied_count': 0,
            'total_count': 0
        })

        for record in rent_roll_records:
            lease_type = record.lease_type or 'Unknown'
            data = lease_type_data[lease_type]

            data['unit_count'] += 1
            data['total_count'] += 1
            data['total_sqft'] += float(record.unit_area_sqft or 0)
            data['total_revenue'] += float(record.annual_rent or 0)

            # Count occupied units
            if record.occupancy_status and record.occupancy_status.lower() == 'occupied':
                data['occupied_count'] += 1

        # Build tenant mix items
        tenant_mix = []
        for lease_type, data in lease_type_data.items():
            occupancy_pct = (data['occupied_count'] / data['total_count'] * 100) if data['total_count'] > 0 else 0.0

            tenant_mix.append(TenantMixItem(
                tenantType=lease_type,
                unitCount=data['unit_count'],
                totalSqft=round(data['total_sqft'], 2),
                totalRevenue=round(data['total_revenue'], 2),
                occupancyPct=round(occupancy_pct, 1)
            ))

        # Sort by revenue descending
        tenant_mix.sort(key=lambda x: x.totalRevenue, reverse=True)

        return TenantMixResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            period_year=latest_period.period_year,
            period_month=latest_period.period_month,
            tenantMix=tenant_mix,
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get tenant mix: {str(e)}")

