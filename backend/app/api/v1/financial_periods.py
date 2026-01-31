"""
Financial Periods API Endpoints

Manage financial periods for properties
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.financial_period import FinancialPeriod
from app.models.period_document_completeness import PeriodDocumentCompleteness
from app.api.dependencies import get_current_user, get_current_organization, require_org_role
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_property_for_org, get_period_for_org
from pydantic import BaseModel

router = APIRouter(prefix="/financial-periods", tags=["financial_periods"])


class FinancialPeriodResponse(BaseModel):
    id: int
    property_id: int
    period_year: int
    period_month: int
    is_closed: bool
    is_complete: bool = False

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
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    List financial periods with optional filters. Tenant-scoped.
    """
    from app.models.property import Property

    query = db.query(FinancialPeriod).join(Property, FinancialPeriod.property_id == Property.id).filter(
        Property.organization_id == current_org.id
    )
    if property_id:
        if not get_property_for_org(db, current_org.id, property_id):
            return []
        query = query.filter(FinancialPeriod.property_id == property_id)

    if period_year:
        query = query.filter(FinancialPeriod.period_year == period_year)

    if period_month:
        query = query.filter(FinancialPeriod.period_month == period_month)

    # Join with PeriodDocumentCompleteness to get is_complete status
    results = query.outerjoin(
        PeriodDocumentCompleteness,
        (PeriodDocumentCompleteness.property_id == FinancialPeriod.property_id) &
        (PeriodDocumentCompleteness.period_id == FinancialPeriod.id)
    ).add_columns(
        PeriodDocumentCompleteness.is_complete
    ).order_by(
        FinancialPeriod.period_year.desc(),
        FinancialPeriod.period_month.desc()
    ).all()

    # Transform results to include is_complete flag
    response = []
    for period, is_complete in results:
        period_dict = {
            "id": period.id,
            "property_id": period.property_id,
            "period_year": period.period_year,
            "period_month": period.period_month,
            "is_closed": period.is_closed,
            "is_complete": is_complete if is_complete is not None else False
        }
        response.append(period_dict)

    return response


@router.get("/{period_id}", response_model=FinancialPeriodResponse)
def get_financial_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get a specific financial period by ID. Tenant-scoped.
    """
    period = get_period_for_org(db, current_org.id, period_id)
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
    current_user=Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
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

    # Check if property exists and belongs to org
    property = get_property_for_org(db, current_org.id, property_id)
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
        organization_id=getattr(property, "organization_id", None),
        period_year=period_year,
        period_month=period_month,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        is_closed=False
    )

    db.add(period)
    db.flush()
    from app.services.audit_service import log_action
    log_action(db, "financial_period.created", current_user.id, current_org.id, "financial_period", str(period.id), f"Created period {period_year}/{period_month}")
    db.commit()
    db.refresh(period)

    return period
