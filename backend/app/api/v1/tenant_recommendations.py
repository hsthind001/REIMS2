"""
Tenant Recommendations API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.database import get_db
from app.services.tenant_recommendation_service import TenantRecommendationService
from app.models.property import Property

router = APIRouter(prefix="/properties", tags=["tenant_recommendations"])
logger = logging.getLogger(__name__)


@router.get("/{property_id}/tenant-recommendations")
def get_tenant_recommendations(
    property_id: int,
    unit_identifier: Optional[str] = None,
    space_sqft: Optional[int] = None,
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered tenant recommendations for vacant space

    Analyzes:
    - Current tenant mix
    - Demographics
    - Market trends
    - Synergy potential
    - Revenue estimates

    Returns top N ranked recommendations with scores
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = TenantRecommendationService(db)

    try:
        result = service.recommend_tenants(
            property_id=property_id,
            unit_identifier=unit_identifier,
            space_sqft=space_sqft,
            top_n=top_n
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))

        return result

    except Exception as e:
        logger.error(f"Tenant recommendation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{property_id}/analyze-tenant-mix")
def analyze_tenant_mix(property_id: int, db: Session = Depends(get_db)):
    """
    Analyze current tenant mix

    Returns:
    - Category distribution
    - Strengths and weaknesses
    - Diversity score
    - Recommendations for improvement
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = TenantRecommendationService(db)

    try:
        result = service.analyze_tenant_mix(property_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))

        return result

    except Exception as e:
        logger.error(f"Tenant mix analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{property_id}/tenant-synergy/{category}")
def calculate_tenant_synergy(
    property_id: int,
    category: str,
    db: Session = Depends(get_db)
):
    """
    Calculate synergy score for a proposed tenant category

    Shows how well the proposed tenant would work with existing tenants
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = TenantRecommendationService(db)

    try:
        result = service.calculate_tenant_synergy(
            property_id=property_id,
            proposed_tenant_category=category
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))

        return result

    except Exception as e:
        logger.error(f"Synergy calculation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{property_id}/tenant-categories")
def get_tenant_categories(db: Session = Depends(get_db)):
    """
    Get list of all tenant categories

    Returns available categories with examples
    """
    service = TenantRecommendationService(db)

    categories = [
        {
            "key": key,
            "name": info.get('name'),
            "examples": info.get('examples'),
            "typical_sqft": info.get('typical_sqft')
        }
        for key, info in service.TENANT_CATEGORIES.items()
    ]

    return {"categories": categories, "total": len(categories)}
