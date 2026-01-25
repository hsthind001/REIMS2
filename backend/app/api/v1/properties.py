from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.property import Property
# Import Organization model for type checking if needed, but dependency returns object
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.api.dependencies import get_current_user, get_current_organization
from app.core.redis_client import invalidate_portfolio_cache
from app.core.config import settings
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/properties", tags=["properties"])


def _maybe_attach_demo_properties(db: Session, current_org) -> None:
    """
    Dev-only helper: if the current org has no properties but demo data exists
    in exactly one other org (with only superuser members), move those properties
    into the current org. This preserves strict tenancy while unblocking local UX.
    """
    if settings.ENVIRONMENT != "development":
        return

    # If org already has properties, do nothing
    has_props = Property.filter_by_org(db.query(Property), current_org.id).limit(1).first()
    if has_props:
        return

    # If there are unassigned properties, attach them to the current org
    null_count = db.query(func.count(Property.id)).filter(Property.organization_id.is_(None)).scalar() or 0
    if null_count:
        updated = db.query(Property).filter(
            Property.organization_id.is_(None)
        ).update(
            {Property.organization_id: current_org.id},
            synchronize_session=False
        )
        if updated:
            db.commit()
            invalidate_portfolio_cache()
            logger.info(
                f"Dev bootstrap: attached {updated} unassigned properties to org {current_org.id}"
            )
        return

    # Find other orgs that have properties
    org_counts = db.query(
        Property.organization_id,
        func.count(Property.id)
    ).filter(
        Property.organization_id != current_org.id
    ).group_by(Property.organization_id).all()

    if not org_counts:
        return

    from app.models.organization import OrganizationMember
    from app.models.user import User

    eligible = []
    for org_id, count in org_counts:
        members = db.query(User.is_superuser).join(
            OrganizationMember, OrganizationMember.user_id == User.id
        ).filter(
            OrganizationMember.organization_id == org_id
        ).all()

        # Allow moving demo data only if there are no members
        # or all members are superusers (dev/seed org)
        if not members or all(m.is_superuser for m in members):
            eligible.append(org_id)

    # Only auto-attach when there's exactly one clear demo org
    if len(eligible) != 1:
        return

    source_org_id = eligible[0]
    updated = db.query(Property).filter(
        Property.organization_id == source_org_id
    ).update(
        {Property.organization_id: current_org.id},
        synchronize_session=False
    )
    if updated:
        db.commit()
        invalidate_portfolio_cache()
        logger.info(
            f"Dev bootstrap: moved {updated} properties from org {source_org_id} to org {current_org.id}"
        )


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Create a new property with unique property_code within organization
    """
    # Check if property_code already exists in this organization
    existing = Property.filter_by_org(db.query(Property), current_org.id)\
        .filter(Property.property_code == property_data.property_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Property with code {property_data.property_code} already exists in this organization"
        )
    
    # Create property with organization_id
    db_property = Property(
        **property_data.model_dump(), 
        created_by=current_user.id,
        organization_id=current_org.id
    )
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    # Invalidate cache for new property
    invalidate_portfolio_cache()
    return db_property


@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    List all properties for the current organization
    """
    _maybe_attach_demo_properties(db, current_org)
    # Enforce tenancy
    query = Property.filter_by_org(db.query(Property), current_org.id)
    
    if status:
        query = query.filter(Property.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{property_code}", response_model=PropertyResponse)
async def get_property(
    property_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Get property by property_code (scoped to organization)
    """
    query = Property.filter_by_org(db.query(Property), current_org.id)
    property = query.filter(Property.property_code == property_code).first()
        
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    return property


@router.put("/{property_code}", response_model=PropertyResponse)
async def update_property(
    property_code: str,
    property_data: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Update property information (scoped to organization)
    """
    query = Property.filter_by_org(db.query(Property), current_org.id)
    property = query.filter(Property.property_code == property_code).first()
        
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    for field, value in property_data.model_dump(exclude_unset=True).items():
        setattr(property, field, value)
    
    db.commit()
    db.refresh(property)
    # Invalidate cache for updated property
    invalidate_portfolio_cache()
    return property


@router.delete("/{property_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Delete property (scoped to organization)
    """
    query = Property.filter_by_org(db.query(Property), current_org.id)
    property = query.filter(Property.property_code == property_code).first()
        
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    db.delete(property)
    db.commit()
    
    # Invalidate portfolio cache to remove deleted property from dashboards
    invalidate_portfolio_cache()
    # logger is not defined at module level yet, but I will add it or use print if simple. 
    # Actually I should add logger definition to be safe.
    
    return None
