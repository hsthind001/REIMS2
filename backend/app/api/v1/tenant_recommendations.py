"""
Tenant Recommendations API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_property_for_org
from app.services.tenant_recommendation_service import TenantRecommendationService

router = APIRouter(prefix="/properties", tags=["tenant_recommendations"])
logger = logging.getLogger(__name__)


# Support both /tenant-recommendations/properties/{id} and /properties/{id}/tenant-recommendations
@router.get("/{property_id}/tenant-recommendations")
def get_tenant_recommendations(
    property_id: int,
    unit_identifier: Optional[str] = None,
    space_sqft: Optional[int] = None,
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
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
    property = get_property_for_org(db, current_org.id, property_id)
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
        return result

    except Exception as e:
        logger.error(f"Failed to get tenant recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Create a separate router for the alternative path
router_alt = APIRouter(prefix="/tenant-recommendations", tags=["tenant_recommendations"])

@router_alt.get("/properties/{property_id}")
def get_tenant_recommendations_alt(
    property_id: int,
    unit_identifier: Optional[str] = None,
    space_sqft: Optional[int] = None,
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
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
    property = get_property_for_org(db, current_org.id, property_id)
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
def analyze_tenant_mix(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Analyze current tenant mix

    Returns:
    - Category distribution
    - Strengths and weaknesses
    - Diversity score
    - Recommendations for improvement
    """
    property = get_property_for_org(db, current_org.id, property_id)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Calculate synergy score for a proposed tenant category

    Shows how well the proposed tenant would work with existing tenants
    """
    property = get_property_for_org(db, current_org.id, property_id)
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
def get_tenant_categories(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get list of all tenant categories

    Returns available categories with examples
    """
    if not get_property_for_org(db, current_org.id, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
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
