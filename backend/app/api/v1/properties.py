from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new property with unique property_code
    """
    # Check if property_code already exists
    existing = db.query(Property).filter(Property.property_code == property_data.property_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Property with code {property_data.property_code} already exists"
        )
    
    # Create property
    db_property = Property(**property_data.model_dump(), created_by=current_user.id)
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
    current_user = Depends(get_current_user)
):
    """
    List all properties with optional filtering by status
    """
    query = db.query(Property)
    if status:
        query = query.filter(Property.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{property_code}", response_model=PropertyResponse)
async def get_property(
    property_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get property by property_code
    """
    property = db.query(Property).filter(Property.property_code == property_code).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    return property


@router.put("/{property_code}", response_model=PropertyResponse)
async def update_property(
    property_code: str,
    property_data: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update property information
    """
    property = db.query(Property).filter(Property.property_code == property_code).first()
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
    current_user = Depends(get_current_user)
):
    """
    Delete property (will cascade to all related data)
    """
    property = db.query(Property).filter(Property.property_code == property_code).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    db.delete(property)
    db.commit()
    return None
