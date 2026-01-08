"""
Financial Periods API Endpoints

Manage financial periods for properties
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from app.api.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/financial-periods", tags=["financial_periods"])


class FinancialPeriodResponse(BaseModel):
    id: int
    property_id: int
    period_year: int
    period_month: int
    is_closed: bool

    class Config:
        from_attributes = True


class FinancialPeriodCreateRequest(BaseModel):
    property_id: int
    period_year: int
    period_month: int


@router.get("/", response_model=List[FinancialPeriodResponse])
def list_financial_periods(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    period_year: Optional[int] = Query(None, description="Filter by year"),
    period_month: Optional[int] = Query(None, description="Filter by month"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List financial periods with optional filters
    """
    query = db.query(FinancialPeriod)

    if property_id:
        query = query.filter(FinancialPeriod.property_id == property_id)

    if period_year:
        query = query.filter(FinancialPeriod.period_year == period_year)

    if period_month:
        query = query.filter(FinancialPeriod.period_month == period_month)

    periods = query.order_by(
        FinancialPeriod.period_year.desc(),
        FinancialPeriod.period_month.desc()
    ).all()

    return periods


@router.get("/{period_id}", response_model=FinancialPeriodResponse)
def get_financial_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific financial period by ID
    """
    period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()

    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    return period


@router.post("/", response_model=FinancialPeriodResponse)
def create_financial_period(
    request: Optional[FinancialPeriodCreateRequest] = Body(None),
    property_id: Optional[int] = Query(None),
    period_year: Optional[int] = Query(None),
    period_month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new financial period (or return existing one)
    """
    if request:
        property_id = request.property_id
        period_year = request.period_year
        period_month = request.period_month

    if property_id is None or period_year is None or period_month is None:
        raise HTTPException(
            status_code=422,
            detail="property_id, period_year, and period_month are required"
        )

    # Check if property exists
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Check if period already exists
    existing = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property_id,
        FinancialPeriod.period_year == period_year,
        FinancialPeriod.period_month == period_month
    ).first()

    if existing:
        return existing

    # Create new period with calculated dates
    from datetime import date
    import calendar

    # Calculate period start and end dates
    period_start_date = date(period_year, period_month, 1)
    last_day = calendar.monthrange(period_year, period_month)[1]
    period_end_date = date(period_year, period_month, last_day)

    period = FinancialPeriod(
        property_id=property_id,
        period_year=period_year,
        period_month=period_month,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        is_closed=False
    )

    db.add(period)
    db.commit()
    db.refresh(period)

    return period
