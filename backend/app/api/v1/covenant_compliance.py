"""
Covenant Compliance API

Covenant compliance history (per-period DSCR, LTV, etc.) for dashboard and audit.
Populated when reconciliation runs (COVENANT-1..6).
Covenant thresholds CRUD for configuration UI.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date

from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_property_for_org
from app.models.covenant_compliance_history import CovenantComplianceHistory
from app.models.covenant_threshold import CovenantThreshold
from app.models.property import Property

router = APIRouter(prefix="/covenant-compliance", tags=["covenant-compliance"])


class CovenantThresholdCreate(BaseModel):
    property_id: int
    covenant_type: str
    threshold_value: float
    comparison_operator: str = ">="
    effective_date: date
    expiration_date: Optional[date] = None
    is_active: bool = True


class CovenantThresholdUpdate(BaseModel):
    threshold_value: Optional[float] = None
    comparison_operator: Optional[str] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    is_active: Optional[bool] = None


class CovenantComplianceHistoryItem(BaseModel):
    id: int
    property_id: int
    period_id: int
    covenant_type: str
    rule_id: str
    calculated_value: Optional[float]
    threshold_value: Optional[float]
    is_compliant: bool
    variance: Optional[float]
    notes: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class CovenantThresholdItem(BaseModel):
    id: int
    property_id: int
    covenant_type: str
    threshold_value: float
    comparison_operator: str
    effective_date: str
    expiration_date: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/history", response_model=List[CovenantComplianceHistoryItem])
def list_covenant_compliance_history(
    property_id: int = Query(..., description="Property ID"),
    period_id: Optional[int] = Query(None, description="Period ID (omit for all periods)"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    List covenant compliance history for a property. Tenant-scoped.
    """
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    q = db.query(CovenantComplianceHistory).filter(
        CovenantComplianceHistory.property_id == property_id
    )
    if period_id is not None:
        q = q.filter(CovenantComplianceHistory.period_id == period_id)
    q = q.order_by(CovenantComplianceHistory.period_id.desc(), CovenantComplianceHistory.covenant_type)
    rows = q.all()
    return [
        CovenantComplianceHistoryItem(
            id=r.id,
            property_id=r.property_id,
            period_id=r.period_id,
            covenant_type=r.covenant_type,
            rule_id=r.rule_id,
            calculated_value=float(r.calculated_value) if r.calculated_value is not None else None,
            threshold_value=float(r.threshold_value) if r.threshold_value is not None else None,
            is_compliant=r.is_compliant,
            variance=float(r.variance) if r.variance is not None else None,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/thresholds", response_model=List[CovenantThresholdItem])
def list_covenant_thresholds(
    property_id: int = Query(..., description="Property ID"),
    include_inactive: bool = Query(False, description="Include inactive thresholds for config UI"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    List per-property covenant thresholds. Tenant-scoped.
    """
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    q = db.query(CovenantThreshold).filter(CovenantThreshold.property_id == property_id)
    if not include_inactive:
        q = q.filter(CovenantThreshold.is_active == True)
    rows = q.order_by(CovenantThreshold.covenant_type, CovenantThreshold.effective_date.desc()).all()
    return [
        CovenantThresholdItem(
            id=r.id,
            property_id=r.property_id,
            covenant_type=r.covenant_type,
            threshold_value=float(r.threshold_value),
            comparison_operator=r.comparison_operator or ">=",
            effective_date=r.effective_date.isoformat() if r.effective_date else "",
            expiration_date=r.expiration_date.isoformat() if r.expiration_date else None,
            is_active=r.is_active,
        )
        for r in rows
    ]


@router.post("/thresholds", response_model=CovenantThresholdItem, status_code=status.HTTP_201_CREATED)
def create_covenant_threshold(
    body: CovenantThresholdCreate,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Create a per-property covenant threshold. Tenant-scoped."""
    if not get_property_for_org(db, current_org.id, body.property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    row = CovenantThreshold(
        property_id=body.property_id,
        covenant_type=body.covenant_type.strip().upper(),
        threshold_value=Decimal(str(body.threshold_value)),
        comparison_operator=body.comparison_operator or ">=",
        effective_date=body.effective_date,
        expiration_date=body.expiration_date,
        is_active=body.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CovenantThresholdItem(
        id=row.id,
        property_id=row.property_id,
        covenant_type=row.covenant_type,
        threshold_value=float(row.threshold_value),
        comparison_operator=row.comparison_operator or ">=",
        effective_date=row.effective_date.isoformat(),
        expiration_date=row.expiration_date.isoformat() if row.expiration_date else None,
        is_active=row.is_active,
    )


@router.patch("/thresholds/{threshold_id}", response_model=CovenantThresholdItem)
def update_covenant_threshold(
    threshold_id: int = Path(..., description="Threshold ID"),
    body: CovenantThresholdUpdate = ...,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Update a covenant threshold. Tenant-scoped."""
    row = db.query(CovenantThreshold).filter(CovenantThreshold.id == threshold_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Covenant threshold not found")
    if not get_property_for_org(db, current_org.id, row.property_id):
        raise HTTPException(status_code=404, detail="Covenant threshold not found")
    if body.threshold_value is not None:
        row.threshold_value = Decimal(str(body.threshold_value))
    if body.comparison_operator is not None:
        row.comparison_operator = body.comparison_operator
    if body.effective_date is not None:
        row.effective_date = body.effective_date
    if body.expiration_date is not None:
        row.expiration_date = body.expiration_date
    if body.is_active is not None:
        row.is_active = body.is_active
    db.commit()
    db.refresh(row)
    return CovenantThresholdItem(
        id=row.id,
        property_id=row.property_id,
        covenant_type=row.covenant_type,
        threshold_value=float(row.threshold_value),
        comparison_operator=row.comparison_operator or ">=",
        effective_date=row.effective_date.isoformat(),
        expiration_date=row.expiration_date.isoformat() if row.expiration_date else None,
        is_active=row.is_active,
    )


@router.delete("/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_covenant_threshold(
    threshold_id: int = Path(..., description="Threshold ID"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Delete a covenant threshold. Tenant-scoped."""
    row = db.query(CovenantThreshold).filter(CovenantThreshold.id == threshold_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Covenant threshold not found")
    if not get_property_for_org(db, current_org.id, row.property_id):
        raise HTTPException(status_code=404, detail="Covenant threshold not found")
    db.delete(row)
    db.commit()
