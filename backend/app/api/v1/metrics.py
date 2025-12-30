"""
Financial Metrics API - Query calculated KPIs and performance metrics
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from functools import lru_cache
import time

from app.db.database import get_db
from app.db.minio_client import get_file_url
from app.services.metrics_service import MetricsService
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.rent_roll_data import RentRollData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.document_upload import DocumentUpload
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache for metrics summary (5-minute TTL)
_metrics_summary_cache = {'data': None, 'timestamp': None, 'ttl': 300}


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
    period_id: Optional[int] = None  # Period ID for API calls
    period_year: int
    period_month: int
    total_assets: Optional[float] = None
    total_revenue: Optional[float] = None
    net_income: Optional[float] = None
    net_operating_income: Optional[float] = None  # NOI for portfolio calculations
    occupancy_rate: Optional[float] = None
    dscr: Optional[float] = None  # Debt Service Coverage Ratio
    ltv_ratio: Optional[float] = None  # Loan-to-Value Ratio

    class Config:
        from_attributes = True


class MetricSourceResponse(BaseModel):
    """Source document information for a metric value"""
    upload_id: int
    document_type: str
    file_name: str
    page_number: Optional[int] = None
    extraction_x0: Optional[float] = None
    extraction_y0: Optional[float] = None
    extraction_x1: Optional[float] = None
    extraction_y1: Optional[float] = None
    pdf_url: Optional[str] = None
    has_coordinates: bool = False


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

    Performance: Implements 5-minute in-memory cache
    """
    try:
        # Check cache first
        cache_key = f"summary_{skip}_{limit}"
        current_time = time.time()

        if (_metrics_summary_cache['data'] is not None and
            _metrics_summary_cache['timestamp'] is not None and
            current_time - _metrics_summary_cache['timestamp'] < _metrics_summary_cache['ttl'] and
            cache_key in _metrics_summary_cache['data']):
            logger.info(f"Returning cached metrics summary (age: {current_time - _metrics_summary_cache['timestamp']:.1f}s)")
            return _metrics_summary_cache['data'][cache_key]

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
                    'period_id': period_id,  # Store period_id for API calls
                    'period_year': year,
                    'period_month': month,
                    'total_assets': metrics.total_assets,
                    'total_revenue': metrics.total_revenue,
                    'net_income': metrics.net_income,
                    'net_operating_income': metrics.net_operating_income,
                    'occupancy_rate': metrics.occupancy_rate,
                    'dscr': metrics.dscr,
                    'ltv_ratio': metrics.ltv_ratio
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
                        current_data['period_id'] = period_id  # Update period_id when period changes
                
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
                period_id=data.get('period_id'),  # Include period_id for API calls
                period_year=data['period_year'],
                period_month=data['period_month'],
                total_assets=float(data['total_assets']) if data['total_assets'] else None,
                total_revenue=float(data['total_revenue']) if data['total_revenue'] else None,
                net_income=float(data['net_income']) if data['net_income'] else None,
                net_operating_income=float(data['net_operating_income']) if data['net_operating_income'] else None,
                occupancy_rate=float(data['occupancy_rate']) if data['occupancy_rate'] else None,
                dscr=float(data['dscr']) if data['dscr'] else None,
                ltv_ratio=float(data['ltv_ratio']) if data['ltv_ratio'] else None
            ))
        
        # Sort by property code for consistent ordering
        summary_items.sort(key=lambda x: x.property_code)

        # Apply pagination
        paginated_items = summary_items[skip:skip + limit]

        # Store in cache
        if _metrics_summary_cache['data'] is None:
            _metrics_summary_cache['data'] = {}
        _metrics_summary_cache['data'][cache_key] = paginated_items
        _metrics_summary_cache['timestamp'] = current_time
        logger.info(f"Cached metrics summary for {len(paginated_items)} properties")

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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    Get metrics over time for trend analysis

    Returns metrics for multiple periods for a property
    Useful for dashboards and charts

    Query params:
    - start_year: Start year (optional)
    - end_year: End year (optional)
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100, max: 500)

    If years not specified, returns all available periods (paginated)
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

        # Apply pagination
        results = query.offset(skip).limit(limit).all()

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


class PortfolioDSCRResponse(BaseModel):
    """Portfolio DSCR response"""
    dscr: float
    yoy_change: float
    total_noi: float
    total_debt_service: float
    properties: List[dict]
    calculation_date: datetime
    note: str

    class Config:
        from_attributes = True


class PortfolioPercentageChangesResponse(BaseModel):
    """Portfolio percentage changes for dashboard"""
    total_value_change: float  # Percentage change for Total Portfolio Value
    noi_change: float  # Percentage change for Portfolio NOI
    occupancy_change: float  # Percentage change for Average Occupancy
    dscr_change: float  # Percentage change for Portfolio DSCR (replaces IRR)
    current_period: dict  # Current period info
    previous_period: dict  # Previous period info
    calculation_date: datetime

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

        # Get most recent metrics WITH actual NOI and total_assets data
        # Don't use periods that only have rent roll data (like April 2025 for ESP001)
        latest_metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.net_operating_income.isnot(None),
            FinancialMetrics.total_assets.isnot(None),
            FinancialMetrics.net_operating_income > 0,
            FinancialMetrics.total_assets > 0
        ).join(FinancialPeriod).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient data to calculate cap rate (need NOI and property value)"
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

    True LTV Formula: (Long-Term Debt / Net Property Value) * 100
    
    Priority:
    1. Use pre-calculated ltv_ratio from FinancialMetrics (preferred)
    2. Calculate from long_term_debt and net_property_value if ltv_ratio is null
    3. Fall back to total_long_term_liabilities / net_property_value if available
    4. Last resort: Use total_liabilities / total_assets (debt-to-assets ratio)
    """
    try:
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # Get latest metrics with data - prioritize records that have at least some relevant data
        latest_metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id
        ).join(FinancialPeriod).order_by(
            # Prioritize records with ltv_ratio first, then by recency
            FinancialMetrics.ltv_ratio.desc().nulls_last(),
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient data to calculate LTV - no financial metrics found"
            )

        # Priority 1: Use pre-calculated ltv_ratio (most accurate)
        if latest_metrics.ltv_ratio is not None:
            ltv = float(latest_metrics.ltv_ratio) * 100  # Convert decimal to percentage
            loan_amount = float(latest_metrics.long_term_debt) if latest_metrics.long_term_debt else float(latest_metrics.total_long_term_liabilities) if latest_metrics.total_long_term_liabilities else 0
            property_value = float(latest_metrics.net_property_value) if latest_metrics.net_property_value else float(latest_metrics.total_property_equipment) if latest_metrics.total_property_equipment else 0
            calculation_method = "ltv_ratio_precalculated"
        
        # Priority 2: Calculate from long_term_debt and net_property_value
        elif latest_metrics.long_term_debt and latest_metrics.net_property_value and latest_metrics.net_property_value > 0:
            loan_amount = float(latest_metrics.long_term_debt)
            property_value = float(latest_metrics.net_property_value)
            ltv = (loan_amount / property_value) * 100
            calculation_method = "long_term_debt_to_net_property_value"
        
        # Priority 3: Calculate from total_long_term_liabilities and net_property_value
        elif latest_metrics.total_long_term_liabilities and latest_metrics.net_property_value and latest_metrics.net_property_value > 0:
            loan_amount = float(latest_metrics.total_long_term_liabilities)
            property_value = float(latest_metrics.net_property_value)
            ltv = (loan_amount / property_value) * 100
            calculation_method = "total_long_term_liabilities_to_net_property_value"
        
        # Priority 4: Fall back to total_long_term_liabilities and total_property_equipment
        elif latest_metrics.total_long_term_liabilities and latest_metrics.total_property_equipment and latest_metrics.total_property_equipment > 0:
            loan_amount = float(latest_metrics.total_long_term_liabilities)
            property_value = float(latest_metrics.total_property_equipment)
            ltv = (loan_amount / property_value) * 100
            calculation_method = "total_long_term_liabilities_to_property_equipment"
        
        # Last resort: Use debt-to-assets ratio (not true LTV, but better than nothing)
        elif latest_metrics.total_liabilities and latest_metrics.total_assets and latest_metrics.total_assets > 0:
            loan_amount = float(latest_metrics.total_liabilities)
            property_value = float(latest_metrics.total_assets)
            ltv = (loan_amount / property_value) * 100
            calculation_method = "debt_to_assets_ratio_fallback"
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient data to calculate LTV - missing required financial metrics"
            )

        debt_to_equity = float(latest_metrics.debt_to_equity_ratio) if latest_metrics.debt_to_equity_ratio else 0

        return LTVResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            ltv=round(ltv, 2),
            loan_amount=loan_amount,
            property_value=property_value,
            debt_to_equity=debt_to_equity,
            calculation_method=calculation_method,
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate LTV: {str(e)}"
        )


@router.get("/exit-strategy/portfolio-dscr", response_model=PortfolioDSCRResponse)
async def get_portfolio_dscr(db: Session = Depends(get_db)):
    """
    Calculate portfolio-wide DSCR from actual financial data
    
    Calculates DSCR for all active properties and returns weighted average:
    - DSCR = NOI / Total Debt Service
    - Portfolio DSCR = Weighted average based on debt service amounts
    """
    try:
        from sqlalchemy import func
        from decimal import Decimal
        
        # Get all active properties
        properties = db.query(Property).filter(Property.status == 'active').all()
        
        if not properties:
            return PortfolioDSCRResponse(
                dscr=0.0,
                yoy_change=0.0,
                total_noi=0.0,
                total_debt_service=0.0,
                properties=[],
                calculation_date=datetime.now(),
                note="No active properties found"
            )
        
        # Find the actual latest period that has income statement data (needed for DSCR)
        # Check which periods have income statements for any property
        from app.models.income_statement_data import IncomeStatementData
        latest_period_with_data = db.query(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            IncomeStatementData, FinancialPeriod.id == IncomeStatementData.period_id
        ).join(
            Property, IncomeStatementData.property_id == Property.id
        ).filter(
            Property.status == 'active'
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()
        
        if not latest_period_with_data:
            return PortfolioDSCRResponse(
                dscr=0.0,
                yoy_change=0.0,
                total_noi=0.0,
                total_debt_service=0.0,
                properties=[],
                calculation_date=datetime.now(),
                note="No income statement data available for DSCR calculation"
            )
        
        current_year = latest_period_with_data.period_year
        current_month = latest_period_with_data.period_month
        
        dscr_service = DSCRMonitoringService(db)
        property_dscrs = []
        total_noi = Decimal('0')
        total_debt_service = Decimal('0')
        
        # Calculate DSCR for each property using the latest period that has data
        for property in properties:
            try:
                # Get period for this property (use latest period with data)
                period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property.id,
                    FinancialPeriod.period_year == current_year,
                    FinancialPeriod.period_month == current_month
                ).first()
                
                if not period:
                    continue
                
                # Calculate DSCR (catch errors for individual properties)
                try:
                    dscr_result = dscr_service.calculate_dscr(property.id, period.id)
                except Exception as prop_err:
                    # Rollback any failed transaction to prevent cascade failures
                    try:
                        db.rollback()
                    except Exception:
                        pass  # Ignore rollback errors
                    # Log but continue with other properties
                    logger.warning(f"Failed to calculate DSCR for property {property.id}: {str(prop_err)}")
                    continue
                
                if dscr_result.get("success"):
                    dscr = Decimal(str(dscr_result["dscr"]))
                    noi = Decimal(str(dscr_result["noi"]))
                    debt_service = Decimal(str(dscr_result["total_debt_service"]))
                    
                    total_noi += noi
                    total_debt_service += debt_service
                    
                    property_dscrs.append({
                        "property_id": property.id,
                        "property_code": property.property_code,
                        "dscr": float(dscr),
                        "noi": float(noi),
                        "debt_service": float(debt_service),
                        "weight": float(debt_service) if total_debt_service > 0 else 0,
                        "status": dscr_result.get("status", "unknown")
                    })
            except Exception as prop_err:
                # Rollback any failed transaction to prevent cascade failures
                try:
                    db.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                # Log but continue with other properties
                logger.warning(f"Error processing property {property.id} for portfolio DSCR: {str(prop_err)}")
                continue
        
        # Calculate portfolio DSCR (weighted average)
        if total_debt_service > 0:
            portfolio_dscr = float(total_noi / total_debt_service)
        else:
            portfolio_dscr = 0.0
        
        # Calculate YoY change - find previous period that has income statement data
        previous_period_with_data = db.query(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            IncomeStatementData, FinancialPeriod.id == IncomeStatementData.period_id
        ).join(
            Property, IncomeStatementData.property_id == Property.id
        ).filter(
            Property.status == 'active',
            # Previous period must be before current period
            (
                (FinancialPeriod.period_year < current_year) |
                (
                    (FinancialPeriod.period_year == current_year) &
                    (FinancialPeriod.period_month < current_month)
                )
            )
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()
        
        prev_year = previous_period_with_data.period_year if previous_period_with_data else current_year
        prev_month = previous_period_with_data.period_month if previous_period_with_data else (current_month - 1 if current_month > 1 else 12)
        if not previous_period_with_data and current_month == 1:
            prev_year = current_year - 1
            prev_month = 12
        
        prev_total_noi = Decimal('0')
        prev_total_debt_service = Decimal('0')
        
        for property in properties:
            try:
                prev_period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property.id,
                    FinancialPeriod.period_year == prev_year,
                    FinancialPeriod.period_month == prev_month
                ).first()
                
                if prev_period:
                    try:
                        prev_dscr_result = dscr_service.calculate_dscr(property.id, prev_period.id)
                        if prev_dscr_result.get("success"):
                            prev_total_noi += Decimal(str(prev_dscr_result["noi"]))
                            prev_total_debt_service += Decimal(str(prev_dscr_result["total_debt_service"]))
                    except Exception as prop_err:
                        # Rollback any failed transaction to prevent cascade failures
                        try:
                            db.rollback()
                        except Exception:
                            pass  # Ignore rollback errors
                        # Log but continue with other properties
                        logger.warning(f"Failed to calculate previous DSCR for property {property.id}: {str(prop_err)}")
                        continue
            except Exception as prop_err:
                # Rollback any failed transaction to prevent cascade failures
                try:
                    db.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                # Log but continue with other properties
                logger.warning(f"Error processing property {property.id} for previous DSCR: {str(prop_err)}")
                continue
        
        prev_portfolio_dscr = 0.0
        if prev_total_debt_service > 0:
            prev_portfolio_dscr = float(prev_total_noi / prev_total_debt_service)
        
        yoy_change = portfolio_dscr - prev_portfolio_dscr
        
        # Calculate weights for property list
        for prop in property_dscrs:
            if total_debt_service > 0:
                prop["weight"] = float(Decimal(str(prop["debt_service"])) / total_debt_service)
            else:
                prop["weight"] = 0
        
        return PortfolioDSCRResponse(
            dscr=round(portfolio_dscr, 2),
            yoy_change=round(yoy_change, 2),
            total_noi=float(total_noi),
            total_debt_service=float(total_debt_service),
            properties=property_dscrs,
            calculation_date=datetime.now(),
            note=f"Calculated from NOI and debt service. Based on {current_year}-{current_month:02d} data."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio DSCR: {str(e)}"
        )


@router.get("/exit-strategy/portfolio-irr", response_model=PortfolioIRRResponse)
async def get_portfolio_irr(db: Session = Depends(get_db)):
    """
    Calculate portfolio-wide IRR from actual financial data
    
    Calculates IRR approximation from:
    - Annual NOI (from income statements)
    - Total Equity (from balance sheets)
    - Uses simplified IRR formula: NOI / Equity * 100 (annualized)
    """
    try:
        from sqlalchemy import func
        from decimal import Decimal
        
        # Get most recent period for all active properties
        latest_period = db.query(
            func.max(FinancialPeriod.period_year).label('max_year'),
            func.max(FinancialPeriod.period_month).label('max_month')
        ).join(
            Property, FinancialPeriod.property_id == Property.id
        ).filter(
            Property.status == 'active'
        ).first()
        
        if not latest_period or not latest_period.max_year:
            # No data available
            return PortfolioIRRResponse(
                irr=0.0,
                yoy_change=0.0,
                properties=[],
                calculation_date=datetime.now(),
                note="No financial data available for IRR calculation"
            )
        
        # Get portfolio totals for current period
        current_metrics = db.query(
            func.sum(FinancialMetrics.net_operating_income).label('total_noi'),
            func.sum(FinancialMetrics.total_equity).label('total_equity')
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialPeriod.period_year == latest_period.max_year,
            FinancialPeriod.period_month == latest_period.max_month
        ).first()
        
        # Get previous period (same month, previous year, or previous month)
        prev_year = latest_period.max_year
        prev_month = latest_period.max_month - 1
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        
        previous_metrics = db.query(
            func.sum(FinancialMetrics.net_operating_income).label('total_noi'),
            func.sum(FinancialMetrics.total_equity).label('total_equity')
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialPeriod.period_year == prev_year,
            FinancialPeriod.period_month == prev_month
        ).first()
        
        # Calculate IRR approximation: Annual NOI / Equity * 100
        # Convert monthly NOI to annual (multiply by 12)
        current_noi = float(current_metrics.total_noi or 0)
        current_equity = float(current_metrics.total_equity or 1)  # Avoid division by zero
        
        # Annualized NOI (assuming monthly data)
        annual_noi = current_noi * 12
        
        # IRR approximation: (Annual NOI / Equity) * 100
        # This is a simplified calculation - true IRR requires cash flow timing
        irr = (annual_noi / current_equity * 100) if current_equity > 0 else 0.0
        
        # Calculate YoY change
        prev_noi = float(previous_metrics.total_noi or 0) if previous_metrics else 0
        prev_equity = float(previous_metrics.total_equity or 1) if previous_metrics else 1
        prev_annual_noi = prev_noi * 12
        prev_irr = (prev_annual_noi / prev_equity * 100) if prev_equity > 0 else 0.0
        
        yoy_change = irr - prev_irr if prev_irr > 0 else 0.0
        
        # Get property-level IRRs
        property_irrs = []
        property_metrics = db.query(
            Property.id,
            Property.property_code,
            FinancialMetrics.net_operating_income,
            FinancialMetrics.total_equity
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialPeriod.period_year == latest_period.max_year,
            FinancialPeriod.period_month == latest_period.max_month,
            FinancialMetrics.total_equity > 0
        ).all()
        
        total_equity_for_weight = sum(float(m.total_equity or 0) for m in property_metrics)
        
        for prop_id, prop_code, noi, equity in property_metrics:
            prop_noi = float(noi or 0) * 12  # Annualize
            prop_equity = float(equity or 1)
            prop_irr = (prop_noi / prop_equity * 100) if prop_equity > 0 else 0.0
            weight = (prop_equity / total_equity_for_weight) if total_equity_for_weight > 0 else 0
            
            property_irrs.append({
                "property_id": prop_id,
                "property_code": prop_code,
                "irr": round(prop_irr, 2),
                "weight": round(weight, 4)
            })
        
        return PortfolioIRRResponse(
            irr=round(irr, 2),
            yoy_change=round(yoy_change, 2),
            properties=property_irrs,
            calculation_date=datetime.now(),
            note=f"Calculated from annualized NOI and equity. Based on {latest_period.max_year}-{latest_period.max_month:02d} data."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio IRR: {str(e)}"
        )


@router.get("/metrics/portfolio-changes", response_model=PortfolioPercentageChangesResponse)
async def get_portfolio_percentage_changes(db: Session = Depends(get_db)):
    """
    Get portfolio percentage changes for dashboard KPIs
    
    Calculates percentage changes for:
    - Total Portfolio Value (total_assets)
    - Portfolio NOI (net_operating_income)
    - Average Occupancy (occupancy_rate)
    - Portfolio IRR
    
    Compares current period to previous period
    """
    try:
        from sqlalchemy import func
        from decimal import Decimal
        
        # Find the actual latest period that has VALID financial metrics data (not NULL)
        latest_period = db.query(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            FinancialMetrics, FinancialPeriod.id == FinancialMetrics.period_id
        ).join(
            Property, FinancialPeriod.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialMetrics.net_operating_income.isnot(None),  # Must have NOI
            FinancialMetrics.total_assets.isnot(None)  # Must have assets
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()
        
        if not latest_period:
            return PortfolioPercentageChangesResponse(
                total_value_change=0.0,
                noi_change=0.0,
                occupancy_change=0.0,
                dscr_change=0.0,
                current_period={"year": None, "month": None},
                previous_period={"year": None, "month": None},
                calculation_date=datetime.now()
            )
        
        current_year = latest_period.period_year
        current_month = latest_period.period_month
        
        # Find the ACTUAL previous period that has VALID data (not just previous month)
        previous_period = db.query(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            FinancialMetrics, FinancialPeriod.id == FinancialMetrics.period_id
        ).join(
            Property, FinancialPeriod.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialMetrics.net_operating_income.isnot(None),  # Must have NOI
            FinancialMetrics.total_assets.isnot(None),  # Must have assets
            # Previous period must be before current period
            (
                (FinancialPeriod.period_year < current_year) |
                (
                    (FinancialPeriod.period_year == current_year) &
                    (FinancialPeriod.period_month < current_month)
                )
            )
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()
        
        prev_year = previous_period.period_year if previous_period else current_year
        prev_month = previous_period.period_month if previous_period else (current_month - 1 if current_month > 1 else 12)
        if not previous_period and current_month == 1:
            prev_year = current_year - 1
            prev_month = 12
        
        # Get current period portfolio totals
        current_totals = db.query(
            func.sum(FinancialMetrics.total_assets).label('total_value'),
            func.sum(FinancialMetrics.net_operating_income).label('total_noi'),
            func.avg(FinancialMetrics.occupancy_rate).label('avg_occupancy')
        ).join(
            FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
        ).join(
            Property, FinancialMetrics.property_id == Property.id
        ).filter(
            Property.status == 'active',
            FinancialPeriod.period_year == current_year,
            FinancialPeriod.period_month == current_month
        ).first()
        
        # Get previous period portfolio totals (only if previous period exists)
        previous_totals = None
        if previous_period:
            previous_totals = db.query(
                func.sum(FinancialMetrics.total_assets).label('total_value'),
                func.sum(FinancialMetrics.net_operating_income).label('total_noi'),
                func.avg(FinancialMetrics.occupancy_rate).label('avg_occupancy')
            ).join(
                FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
            ).join(
                Property, FinancialMetrics.property_id == Property.id
            ).filter(
                Property.status == 'active',
                FinancialPeriod.period_year == prev_year,
                FinancialPeriod.period_month == prev_month
            ).first()
        
        # Calculate percentage changes
        def calc_change(current, previous):
            if not previous or previous == 0:
                return 0.0
            return ((current - previous) / previous) * 100
        
        current_value = float(current_totals.total_value or 0)
        prev_value = float(previous_totals.total_value or 0) if previous_totals else 0
        value_change = calc_change(current_value, prev_value)
        
        current_noi = float(current_totals.total_noi or 0)
        prev_noi = float(previous_totals.total_noi or 0) if previous_totals else 0
        noi_change = calc_change(current_noi, prev_noi)
        
        current_occ = float(current_totals.avg_occupancy or 0)
        prev_occ = float(previous_totals.avg_occupancy or 0) if previous_totals else 0
        occupancy_change = calc_change(current_occ, prev_occ)
        
        # Calculate DSCR change
        from decimal import Decimal
        dscr_service = DSCRMonitoringService(db)
        current_dscr = 0.0
        prev_dscr = 0.0
        
        # Get all active properties for current period
        properties = db.query(Property).filter(Property.status == 'active').all()
        
        current_total_noi = Decimal('0')
        current_total_debt_service = Decimal('0')
        prev_total_noi = Decimal('0')
        prev_total_debt_service = Decimal('0')
        
        for property in properties:
            try:
                # Current period DSCR
                current_period_obj = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property.id,
                    FinancialPeriod.period_year == current_year,
                    FinancialPeriod.period_month == current_month
                ).first()
                
                if current_period_obj:
                    try:
                        dscr_result = dscr_service.calculate_dscr(property.id, current_period_obj.id)
                        if dscr_result.get("success"):
                            current_total_noi += Decimal(str(dscr_result["noi"]))
                            current_total_debt_service += Decimal(str(dscr_result["total_debt_service"]))
                    except Exception as prop_err:
                        logger.warning(f"Failed to calculate current DSCR for property {property.id}: {str(prop_err)}")
                
                # Previous period DSCR
                prev_period_obj = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property.id,
                    FinancialPeriod.period_year == prev_year,
                    FinancialPeriod.period_month == prev_month
                ).first()
                
                if prev_period_obj:
                    try:
                        prev_dscr_result = dscr_service.calculate_dscr(property.id, prev_period_obj.id)
                        if prev_dscr_result.get("success"):
                            prev_total_noi += Decimal(str(prev_dscr_result["noi"]))
                            prev_total_debt_service += Decimal(str(prev_dscr_result["total_debt_service"]))
                    except Exception as prop_err:
                        logger.warning(f"Failed to calculate previous DSCR for property {property.id}: {str(prop_err)}")
            except Exception as prop_err:
                logger.warning(f"Error processing property {property.id} for portfolio changes: {str(prop_err)}")
                continue
        
        if current_total_debt_service > 0:
            current_dscr = float(current_total_noi / current_total_debt_service)
        if prev_total_debt_service > 0:
            prev_dscr = float(prev_total_noi / prev_total_debt_service)
        
        dscr_change = current_dscr - prev_dscr
        
        return PortfolioPercentageChangesResponse(
            total_value_change=round(value_change, 2),
            noi_change=round(noi_change, 2),
            occupancy_change=round(occupancy_change, 2),
            dscr_change=round(dscr_change, 2),
            current_period={"year": current_year, "month": current_month},
            previous_period={"year": previous_period.period_year if previous_period else None, 
                           "month": previous_period.period_month if previous_period else None},
            calculation_date=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio percentage changes: {str(e)}"
        )


class DSCRHistoricalResponse(BaseModel):
    """Historical DSCR data for sparkline visualization"""
    property_id: int
    property_code: str
    months: int
    dscr_values: List[float]
    periods: List[dict]
    calculated_at: datetime

    class Config:
        from_attributes = True


@router.get("/metrics/{property_id}/dscr/historical", response_model=DSCRHistoricalResponse)
async def get_historical_dscr(
    property_id: int = Path(..., description="Property ID"),
    months: int = Query(12, ge=1, le=60, description="Number of months of historical data"),
    db: Session = Depends(get_db)
):
    """
    Get historical DSCR values for a property for sparkline visualization
    
    Calculates DSCR for each available period in the last N months.
    Returns DSCR values and period information for charting.
    """
    try:
        from decimal import Decimal
        
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )
        
        # Get periods for the property, ordered by date (most recent first)
        periods = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(
            FinancialPeriod.period_end_date.desc()
        ).limit(months).all()
        
        if not periods:
            return DSCRHistoricalResponse(
                property_id=property_id,
                property_code=property_obj.property_code,
                months=0,
                dscr_values=[],
                periods=[],
                calculated_at=datetime.now()
            )
        
        # Reverse to get chronological order (oldest first)
        periods = list(reversed(periods))
        
        # Calculate DSCR for each period
        dscr_service = DSCRMonitoringService(db)
        dscr_values = []
        period_data = []
        
        for period in periods:
            try:
                dscr_result = dscr_service.calculate_dscr(property_id, period.id)
                if dscr_result.get("success"):
                    dscr_values.append(float(dscr_result["dscr"]))
                    period_data.append({
                        "period_id": period.id,
                        "year": period.period_year,
                        "month": period.period_month,
                        "end_date": period.period_end_date.isoformat() if period.period_end_date else None,
                        "dscr": float(dscr_result["dscr"]),
                        "noi": float(dscr_result["noi"]),
                        "debt_service": float(dscr_result["total_debt_service"])
                    })
                else:
                    # Skip periods where DSCR cannot be calculated
                    logger.debug(f"Skipping period {period.id} for property {property_id}: {dscr_result.get('error')}")
            except Exception as e:
                logger.warning(f"Failed to calculate DSCR for property {property_id}, period {period.id}: {str(e)}")
                continue
        
        return DSCRHistoricalResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            months=len(dscr_values),
            dscr_values=dscr_values,
            periods=period_data,
            calculated_at=datetime.now()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical DSCR for property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical DSCR: {str(e)}"
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

        # Get latest period WITH actual income statement line items (not just metrics)
        # We need detailed expense breakdown from income_statement_data table
        from app.models.income_statement_data import IncomeStatementData
        from app.models.income_statement_header import IncomeStatementHeader

        # Find the latest period that has income statement data
        latest_period_with_data = db.query(
            FinancialPeriod.id,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            IncomeStatementData,
            IncomeStatementData.period_id == FinancialPeriod.id
        ).filter(
            FinancialPeriod.property_id == property_id
        ).group_by(
            FinancialPeriod.id,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).order_by(
            FinancialPeriod.period_year.desc(),
            FinancialPeriod.period_month.desc()
        ).first()

        if not latest_period_with_data:
            raise HTTPException(404, "No income statement data found for property")

        period_id, year, month = latest_period_with_data

        # Get financial metrics for this period (for total_expenses)
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        # Get income statement header for this period
        income_header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == property_id,
            IncomeStatementHeader.period_id == period_id
        ).first()
        
        costs = {
            "insurance": 0.0,
            "mortgage": 0.0,
            "utilities": 0.0,
            "maintenance": 0.0,
            "taxes": 0.0,
            "other": 0.0
        }
        
        # Get expense line items from income statement
        # Try with header_id first if header exists, then fall back to period_id only
        expense_items = []
        if income_header:
            expense_items = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.header_id == income_header.id
            ).all()

        # If no items found with header_id, try without header_id (some data might not have header)
        if not expense_items:
            expense_items = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            ).all()
        
        if expense_items:
            for item in expense_items:
                account_code = item.account_code or ''
                account_name = (item.account_name or '').upper()
                amount = float(item.period_amount or 0)

                # Skip revenue accounts (4000 series) - only process expense accounts (5000+)
                if account_code.startswith('4') or account_code.startswith('3'):
                    continue

                # Map account codes to expense categories based on Chart of Accounts
                # Only match expenses (5xxx, 6xxx, 7xxx, 8xxx series)
                if account_code.startswith('5012') or (account_code.startswith('5') and 'INSURANCE' in account_name):
                    costs["insurance"] += amount
                elif account_code.startswith('7000') or (account_code.startswith('7') and ('MORTGAGE' in account_name or 'INTEREST' in account_name)):
                    costs["mortgage"] += amount
                elif account_code.startswith('5100') or account_code.startswith('5105') or account_code.startswith('5115') or account_code.startswith('5125') or account_code.startswith('5199') or (account_code.startswith('5') and ('UTILITY' in account_name or 'ELECTRIC' in account_name or 'WATER' in account_name)):
                    costs["utilities"] += amount
                elif account_code.startswith('5040') or account_code.startswith('5200') or account_code.startswith('5210') or account_code.startswith('53') or (account_code.startswith('5') and ('MAINTENANCE' in account_name or 'REPAIR' in account_name or 'R&M' in account_name)):
                    costs["maintenance"] += amount
                elif account_code.startswith('5010') or account_code.startswith('5014') or (account_code.startswith('5') and 'TAX' in account_name):
                    costs["taxes"] += amount
                elif account_code.startswith('8') or (amount < 0 and account_code.startswith('5')):
                    # Other expenses (8000 series or negative expense amounts)
                    costs["other"] += abs(amount)
        
        # Round all costs
        costs = {k: round(v, 2) for k, v in costs.items()}
        
        # Calculate total as sum of all operating expense categories
        # This represents Total Annual Operating Expenses (Insurance + Mortgage + Utilities + Maintenance + Taxes + Other)
        # Note: Initial Buying (purchase price) is NOT included as it's a one-time cost, not an annual expense
        total_operating_expenses = sum(costs.values())
        
        # Use total_expenses from metrics if available and reasonable, otherwise use calculated sum
        # total_expenses from metrics might include other expenses not categorized above
        if metrics and metrics.total_expenses and metrics.total_expenses > 0:
            # Use metrics total if it's close to our calculated sum (within 10%)
            # Only compare if we have calculated expenses to avoid division by zero
            if total_operating_expenses > 0 and abs(float(metrics.total_expenses) - total_operating_expenses) / total_operating_expenses < 0.1:
                total_operating_expenses = float(metrics.total_expenses)
            elif total_operating_expenses == 0:
                # If we have no calculated expenses but metrics has total_expenses, use it
                total_operating_expenses = float(metrics.total_expenses)
            # Otherwise use calculated sum (more accurate breakdown)

        return PropertyCostsResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            period_year=year,
            period_month=month,
            costs=costs,
            total_costs=round(total_operating_expenses, 2),
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
    period_id: Optional[int] = Query(None, description="Financial period ID (optional, defaults to latest)"),
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
    - Based on specified period or latest financial period rent roll
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )

        # Get financial period - use specified period_id or latest
        if period_id:
            latest_period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id,
                FinancialPeriod.property_id == property_id
            ).first()
        else:
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
        
        # If no rent roll found for this period, try latest available rent roll
        if not rent_roll_records:
            latest_rent_roll_period = (
                db.query(FinancialPeriod)
                .join(RentRollData, RentRollData.period_id == FinancialPeriod.id)
                .filter(
                    RentRollData.property_id == property_id,
                    RentRollData.is_gross_rent_row == False
                )
                .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
                .first()
            )
            
            if latest_rent_roll_period:
                rent_roll_records = (
                    db.query(RentRollData)
                    .filter(
                        RentRollData.property_id == property_id,
                        RentRollData.period_id == latest_rent_roll_period.id,
                        RentRollData.is_gross_rent_row == False
                    )
                    .order_by(RentRollData.unit_number)
                    .limit(limit)
                    .all()
                )
                # Update latest_period to the rent roll period
                if rent_roll_records:
                    latest_period = latest_rent_roll_period

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

            # Format date as MM/DD/YYYY to avoid timezone conversion issues
            lease_end_formatted = None
            if record.lease_end_date:
                lease_end_formatted = record.lease_end_date.strftime('%m/%d/%Y')
            
            unit_info = UnitInfo(
                unitNumber=record.unit_number,
                sqft=float(record.unit_area_sqft or 0),
                status=status_str,
                tenant=record.tenant_name if status_str == 'occupied' else None,
                monthlyRent=float(record.monthly_rent) if record.monthly_rent else None,
                leaseEndDate=lease_end_formatted
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


class TenantDetailItem(BaseModel):
    """Complete tenant information from rent roll"""
    id: int
    unit_number: str
    tenant_name: str
    tenant_code: Optional[str] = None
    lease_type: Optional[str] = None
    lease_start_date: Optional[str] = None
    lease_end_date: Optional[str] = None
    lease_term_months: Optional[int] = None
    remaining_lease_years: Optional[float] = None
    unit_area_sqft: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_rent_per_sqft: Optional[float] = None
    annual_rent: Optional[float] = None
    annual_rent_per_sqft: Optional[float] = None
    gross_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    loc_amount: Optional[float] = None
    annual_cam_reimbursement: Optional[float] = None
    annual_tax_reimbursement: Optional[float] = None
    annual_insurance_reimbursement: Optional[float] = None
    tenancy_years: Optional[float] = None
    annual_recoveries_per_sf: Optional[float] = None
    annual_misc_per_sf: Optional[float] = None
    occupancy_status: Optional[str] = None
    lease_status: Optional[str] = None
    notes: Optional[str] = None
    period_year: int
    period_month: int

    class Config:
        from_attributes = True


class TenantDetailsResponse(BaseModel):
    """Complete tenant list with all rent roll columns"""
    property_id: int
    property_code: str
    period_year: int
    period_month: int
    total_tenants: int
    tenants: List[TenantDetailItem]


@router.get("/metrics/{property_id}/tenants", response_model=TenantDetailsResponse)
async def get_all_tenants(
    property_id: int = Path(..., description="Property ID"),
    period_id: Optional[int] = Query(None, description="Optional: Specific period ID. If not provided, uses latest rent roll period"),
    db: Session = Depends(get_db)
):
    """
    Get all tenant information from rent roll data
    
    Returns comprehensive tenant data with ALL columns from rent_roll_data table:
    - Tenant Information (name, code, unit number)
    - Lease Information (type, dates, term, remaining years)
    - Space Information (square footage)
    - Financial Information (rents, deposits, reimbursements)
    - Status Information (occupancy, lease status)
    - Additional Details (notes, recoveries, misc charges)
    
    Uses latest rent roll period if period_id not specified.
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(404, f"Property {property_id} not found")
        
        # Determine which period to use
        if period_id:
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id,
                FinancialPeriod.property_id == property_id
            ).first()
            if not period:
                raise HTTPException(404, f"Period {period_id} not found for property {property_id}")
        else:
            # Find latest period with rent roll data
            period = (
                db.query(FinancialPeriod)
                .join(RentRollData, RentRollData.period_id == FinancialPeriod.id)
                .filter(
                    RentRollData.property_id == property_id,
                    RentRollData.is_gross_rent_row == False
                )
                .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
                .first()
            )
            
            if not period:
                raise HTTPException(404, f"No rent roll data found for property {property_id}")
        
        # Query all rent roll data for this property and period
        rent_roll_records = (
            db.query(RentRollData)
            .filter(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period.id,
                RentRollData.is_gross_rent_row == False  # Exclude gross rent calculation rows
            )
            .order_by(RentRollData.unit_number)
            .all()
        )
        
        # Build tenant list with all columns
        tenants = []
        for record in rent_roll_records:
            # Format dates as MM/DD/YYYY to avoid timezone conversion issues in frontend
            lease_start_formatted = None
            if record.lease_start_date:
                lease_start_formatted = record.lease_start_date.strftime('%m/%d/%Y')
            
            lease_end_formatted = None
            if record.lease_end_date:
                lease_end_formatted = record.lease_end_date.strftime('%m/%d/%Y')
            
            tenant = TenantDetailItem(
                id=record.id,
                unit_number=record.unit_number,
                tenant_name=record.tenant_name,
                tenant_code=record.tenant_code,
                lease_type=record.lease_type,
                lease_start_date=lease_start_formatted,
                lease_end_date=lease_end_formatted,
                lease_term_months=record.lease_term_months,
                remaining_lease_years=float(record.remaining_lease_years) if record.remaining_lease_years else None,
                unit_area_sqft=float(record.unit_area_sqft) if record.unit_area_sqft else None,
                monthly_rent=float(record.monthly_rent) if record.monthly_rent else None,
                monthly_rent_per_sqft=float(record.monthly_rent_per_sqft) if record.monthly_rent_per_sqft else None,
                annual_rent=float(record.annual_rent) if record.annual_rent else None,
                annual_rent_per_sqft=float(record.annual_rent_per_sqft) if record.annual_rent_per_sqft else None,
                gross_rent=float(record.gross_rent) if record.gross_rent else None,
                security_deposit=float(record.security_deposit) if record.security_deposit else None,
                loc_amount=float(record.loc_amount) if record.loc_amount else None,
                annual_cam_reimbursement=float(record.annual_cam_reimbursement) if record.annual_cam_reimbursement else None,
                annual_tax_reimbursement=float(record.annual_tax_reimbursement) if record.annual_tax_reimbursement else None,
                annual_insurance_reimbursement=float(record.annual_insurance_reimbursement) if record.annual_insurance_reimbursement else None,
                tenancy_years=float(record.tenancy_years) if record.tenancy_years else None,
                annual_recoveries_per_sf=float(record.annual_recoveries_per_sf) if record.annual_recoveries_per_sf else None,
                annual_misc_per_sf=float(record.annual_misc_per_sf) if record.annual_misc_per_sf else None,
                occupancy_status=record.occupancy_status,
                lease_status=record.lease_status,
                notes=record.notes,
                period_year=period.period_year,
                period_month=period.period_month
            )
            tenants.append(tenant)
        
        return TenantDetailsResponse(
            property_id=property_id,
            property_code=property_obj.property_code,
            period_year=period.period_year,
            period_month=period.period_month,
            total_tenants=len(tenants),
            tenants=tenants
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get tenant details: {str(e)}")


@router.get("/metrics/{property_id}/source", response_model=MetricSourceResponse)
async def get_metric_source(
    property_id: int = Path(..., description="Property ID"),
    account_code: Optional[str] = Query(None, description="Account code (e.g., '1999-0000' for Total Assets)"),
    metric_type: Optional[str] = Query(None, description="Metric type: 'total_assets', 'net_operating_income', 'occupancy_rate'"),
    period_id: Optional[int] = Query(None, description="Financial period ID (optional, uses latest if not provided)"),
    db: Session = Depends(get_db)
):
    """
    Get source document information for a metric value
    
    Returns the PDF document and coordinates where the metric value was extracted from.
    Used for PDF source navigation feature.
    
    Query params:
    - account_code: Account code to look up (e.g., '1999-0000' for Total Assets)
    - metric_type: Type of metric ('total_assets', 'net_operating_income', 'occupancy_rate')
    - period_id: Financial period ID (optional, uses most recent if not provided)
    
    Returns:
    - upload_id: Document upload ID
    - document_type: Type of document (balance_sheet, income_statement, etc.)
    - page_number: Page number in PDF
    - coordinates: Extraction coordinates (x0, y0, x1, y1)
    - pdf_url: Presigned URL to access the PDF
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_id} not found")
        
        # Determine which table to query based on metric_type or account_code
        source_record = None
        document_type = None
        
        # Map metric types to account codes if needed
        if metric_type == 'total_assets' or metric_type == 'property_value':
            account_code = account_code or '1999-0000'
        elif metric_type == 'net_operating_income':
            # NOI is typically calculated, but we can look for the income statement
            document_type = 'income_statement'
        
        # Get period if not provided
        if not period_id:
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id
            ).order_by(
                FinancialPeriod.period_year.desc(),
                FinancialPeriod.period_month.desc()
            ).first()
            if not period:
                raise HTTPException(status_code=404, detail=f"No financial periods found for property {property_id}")
            period_id = period.id
        else:
            period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
            if not period:
                raise HTTPException(status_code=404, detail=f"Period {period_id} not found")
        
        # Query balance sheet data if account_code is provided
        # First try the requested period, then try other periods if not found
        if account_code:
            source_record = db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id,
                BalanceSheetData.account_code == account_code
            ).order_by(
                BalanceSheetData.id.desc()
            ).first()
            
            if source_record:
                document_type = 'balance_sheet'
            else:
                # If not found in requested period, search across all periods for this property
                source_record = db.query(BalanceSheetData).filter(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.account_code == account_code
                ).order_by(
                    BalanceSheetData.period_id.desc(),
                    BalanceSheetData.id.desc()
                ).first()
                
                if source_record:
                    document_type = 'balance_sheet'
                    # Update period_id to match the found record
                    period_id = source_record.period_id
                    period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        
        # If not found in balance sheet, try income statement
        if not source_record and account_code:
            source_record = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code == account_code
            ).order_by(
                IncomeStatementData.id.desc()
            ).first()
            
            if source_record:
                document_type = 'income_statement'
            else:
                # If not found in requested period, search across all periods for this property
                source_record = db.query(IncomeStatementData).filter(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.account_code == account_code
                ).order_by(
                    IncomeStatementData.period_id.desc(),
                    IncomeStatementData.id.desc()
                ).first()
                
                if source_record:
                    document_type = 'income_statement'
                    # Update period_id to match the found record
                    period_id = source_record.period_id
                    period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        
        # If still not found and metric_type is net_operating_income, look for NOI line
        if not source_record and metric_type == 'net_operating_income':
            source_record = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.is_total == True,
                IncomeStatementData.line_category == 'SUMMARY'
            ).order_by(
                IncomeStatementData.id.desc()
            ).first()
            
            if source_record:
                document_type = 'income_statement'
        
        # If still not found, try to get any document for this property/period as fallback
        if not source_record:
            # Try balance sheet first
            fallback_record = db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            ).order_by(BalanceSheetData.id.desc()).first()
            
            if fallback_record:
                source_record = fallback_record
                document_type = 'balance_sheet'
            else:
                # Try income statement
                fallback_record = db.query(IncomeStatementData).filter(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id
                ).order_by(IncomeStatementData.id.desc()).first()
                
                if fallback_record:
                    source_record = fallback_record
                    document_type = 'income_statement'
        
        if not source_record:
            raise HTTPException(
                status_code=404,
                detail=f"Source document not found for property {property_id}, account_code={account_code}, metric_type={metric_type}. Please ensure documents have been uploaded and extracted."
            )
        
        # Get document upload
        upload = db.query(DocumentUpload).filter(DocumentUpload.id == source_record.upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail=f"Document upload {source_record.upload_id} not found")
        
        # Get PDF URL - use backend-proxied endpoint to avoid CORS issues
        pdf_url = None
        if upload.file_path:
            # Use backend streaming endpoint instead of presigned URL
            from app.core.config import settings
            import os
            backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
            pdf_url = f"{backend_url}{settings.API_V1_STR}/pdf-viewer/{upload.id}/stream"
        
        # Extract coordinates
        has_coordinates = (
            source_record.extraction_x0 is not None and
            source_record.extraction_y0 is not None and
            source_record.extraction_x1 is not None and
            source_record.extraction_y1 is not None
        )
        
        # If coordinates are missing, try to extract them from PDF on-the-fly
        extraction_x0 = float(source_record.extraction_x0) if source_record.extraction_x0 else None
        extraction_y0 = float(source_record.extraction_y0) if source_record.extraction_y0 else None
        extraction_x1 = float(source_record.extraction_x1) if source_record.extraction_x1 else None
        extraction_y1 = float(source_record.extraction_y1) if source_record.extraction_y1 else None
        page_num = source_record.page_number
        
        if not has_coordinates and account_code:
            try:
                # Try to find the account code in the PDF
                from app.db.minio_client import download_file
                import fitz
                
                pdf_data = download_file(upload.file_path)
                if pdf_data:
                    doc = fitz.open(stream=pdf_data, filetype='pdf')
                    # Search for account code or related text
                    search_terms = [account_code]
                    if account_code == '1999-0000':
                        search_terms.append('TOTAL ASSETS')
                    
                    for page_idx in range(len(doc)):
                        page = doc[page_idx]
                        for term in search_terms:
                            text_instances = page.search_for(term)
                            if text_instances:
                                # Use the first instance found
                                rect = text_instances[0]
                                extraction_x0 = rect.x0
                                extraction_y0 = rect.y0
                                extraction_x1 = rect.x1
                                extraction_y1 = rect.y1
                                page_num = page_idx + 1
                                has_coordinates = True
                                break
                        if has_coordinates:
                            break
                    doc.close()
            except Exception as e:
                print(f"Could not extract coordinates from PDF: {e}")
        
        return MetricSourceResponse(
            upload_id=upload.id,
            document_type=document_type or upload.document_type,
            file_name=upload.file_name,
            page_number=page_num,
            extraction_x0=extraction_x0,
            extraction_y0=extraction_y0,
            extraction_x1=extraction_x1,
            extraction_y1=extraction_y1,
            pdf_url=pdf_url,
            has_coordinates=has_coordinates
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metric source: {str(e)}"
        )


@router.get("/metrics/{property_id}/dscr/latest-complete")
def get_dscr_for_latest_complete_period(
    property_id: int,
    year: int = Query(..., description="Year to check for complete periods"),
    db: Session = Depends(get_db)
):
    """
    Calculate DSCR for the latest period where all required documents are available.

    Required documents: balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement
    """
    try:
        from app.services.dscr_monitoring_service import DSCRMonitoringService
        from app.models.mortgage_statement_data import MortgageStatementData
        from app.models.document_upload import DocumentUpload

        # Get all periods for the property and year, ordered by most recent first
        periods = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == year
        ).order_by(
            FinancialPeriod.period_month.desc()
        ).all()

        if not periods:
            raise HTTPException(
                status_code=404,
                detail=f"No financial periods found for property {property_id} in year {year}"
            )

        # Required document types
        required_doc_types = ['balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement']

        # Find the latest complete period
        latest_complete_period = None
        for period in periods:
            # Get all uploaded documents for this period
            uploaded_docs = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period.id,
                DocumentUpload.extraction_status == 'completed'
            ).all()

            # Create a set of available document types
            available_types = {doc.document_type for doc in uploaded_docs}

            # Check for mortgage statement data
            has_mortgage_data = db.query(MortgageStatementData).filter(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period.id
            ).first() is not None

            if has_mortgage_data:
                available_types.add('mortgage_statement')

            # Check if all required documents are available
            if all(doc_type in available_types for doc_type in required_doc_types):
                latest_complete_period = period
                break

        if not latest_complete_period:
            return {
                "property_id": property_id,
                "year": year,
                "dscr": None,
                "period": None,
                "message": "No complete period found (missing required documents)",
                "missing_documents": True
            }

        # Calculate DSCR for this period
        dscr_service = DSCRMonitoringService(db)
        dscr_result = dscr_service.calculate_dscr(property_id, latest_complete_period.id)

        if not dscr_result.get("success"):
            return {
                "property_id": property_id,
                "year": year,
                "dscr": None,
                "period": {
                    "period_id": latest_complete_period.id,
                    "month": latest_complete_period.period_month,
                    "year": latest_complete_period.period_year
                },
                "error": dscr_result.get("error"),
                "calculation_failed": True
            }

        return {
            "property_id": property_id,
            "year": year,
            "dscr": dscr_result.get("dscr"),
            "noi": dscr_result.get("noi"),
            "total_debt_service": dscr_result.get("total_debt_service"),
            "status": dscr_result.get("status"),
            "period": {
                "period_id": latest_complete_period.id,
                "month": latest_complete_period.period_month,
                "year": latest_complete_period.period_year
            },
            "threshold_breached": dscr_result.get("threshold_breached"),
            "calculated_at": dscr_result.get("calculated_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to calculate DSCR for latest complete period: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate DSCR: {str(e)}"
        )
