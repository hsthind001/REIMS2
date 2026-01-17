from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.property import Property
# Import Organization model for type checking if needed, but dependency returns object
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.api.dependencies import get_current_user, get_current_organization

router = APIRouter(prefix="/properties", tags=["properties"])


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
    # Check if property_code already exists IN THIS ORGANIZATION
    # (Optional: property_code could be globally unique or per-org. Assuming per-org is better for SaaS)
    query = db.query(Property)
    existing = Property.filter_by_org(query, current_org.id)\
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
    query = db.query(Property)
    # Enforce Tenancy
    query = Property.filter_by_org(query, current_org.id)
    
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
    query = db.query(Property)
    property = Property.filter_by_org(query, current_org.id)\
        .filter(Property.property_code == property_code).first()
        
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
    query = db.query(Property)
    property = Property.filter_by_org(query, current_org.id)\
        .filter(Property.property_code == property_code).first()
        
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    for field, value in property_data.model_dump(exclude_unset=True).items():
        setattr(property, field, value)
    
    db.commit()
    db.refresh(property)
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
    query = db.query(Property)
    property = Property.filter_by_org(query, current_org.id)\
        .filter(Property.property_code == property_code).first()
        
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    db.delete(property)
    db.commit()
    return None
