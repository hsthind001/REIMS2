"""
Property Research API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.database import get_db
from app.services.property_research_service import PropertyResearchService
from app.models.property import Property

router = APIRouter(prefix="/properties", tags=["property_research"])
logger = logging.getLogger(__name__)


@router.post("/{property_id}/research")
async def trigger_property_research(
    property_id: int,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger comprehensive property research

    - Gathers demographics (Census Bureau)
    - Employment data (BLS)
    - Market analysis (Google Places)
    - Nearby developments

    Results are cached for 30 days unless force_refresh=True
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = PropertyResearchService(db)

    try:
        result = await service.conduct_research(property_id, force_refresh)
        return result
    except Exception as e:
        logger.error(f"Research failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{property_id}/research/latest")
def get_latest_research(property_id: int, db: Session = Depends(get_db)):
    """Get most recent research data for property"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = PropertyResearchService(db)
    research = service.get_latest_research(property_id)

    if not research:
        raise HTTPException(status_code=404, detail="No research data available")

    return research.to_dict()


@router.get("/{property_id}/demographics")
def get_demographics(property_id: int, db: Session = Depends(get_db)):
    """Get demographics data only"""
    service = PropertyResearchService(db)
    demographics = service.get_demographics(property_id)

    if not demographics:
        raise HTTPException(status_code=404, detail="No demographics data available")

    return {"property_id": property_id, "demographics": demographics}


@router.get("/{property_id}/employment")
def get_employment_data(property_id: int, db: Session = Depends(get_db)):
    """Get employment data only"""
    service = PropertyResearchService(db)
    employment = service.get_employment_data(property_id)

    if not employment:
        raise HTTPException(status_code=404, detail="No employment data available")

    return {"property_id": property_id, "employment": employment}


@router.get("/{property_id}/developments")
def get_nearby_developments(property_id: int, db: Session = Depends(get_db)):
    """Get nearby development projects"""
    service = PropertyResearchService(db)
    developments = service.get_nearby_developments(property_id)

    return {
        "property_id": property_id,
        "developments": developments,
        "count": len(developments)
    }


@router.get("/{property_id}/market-analysis")
def get_market_analysis(property_id: int, db: Session = Depends(get_db)):
    """Get market analysis data"""
    service = PropertyResearchService(db)
    market = service.get_market_analysis(property_id)

    if not market:
        raise HTTPException(status_code=404, detail="No market data available")

    return {"property_id": property_id, "market_analysis": market}


@router.get("/{property_id}/market-health")
def get_market_health_score(property_id: int, db: Session = Depends(get_db)):
    """
    Get overall market health score (0-100)

    Combines demographics, employment, and market data
    """
    service = PropertyResearchService(db)
    result = service.generate_market_health_score(property_id)

    if not result['success']:
        raise HTTPException(status_code=404, detail=result.get('error'))

    return result


@router.get("/{property_id}/trends/demographics")
def get_demographic_trends(
    property_id: int,
    years: int = 5,
    db: Session = Depends(get_db)
):
    """Get demographic trends over time"""
    service = PropertyResearchService(db)
    result = service.get_demographic_trends(property_id, years)

    if not result['success']:
        raise HTTPException(status_code=404, detail=result.get('error'))

    return result


@router.get("/{property_id}/trends/employment")
def get_employment_trends(
    property_id: int,
    years: int = 5,
    db: Session = Depends(get_db)
):
    """Get employment trends over time"""
    service = PropertyResearchService(db)
    result = service.get_employment_trends(property_id, years)

    if not result['success']:
        raise HTTPException(status_code=404, detail=result.get('error'))

    return result


@router.get("/{property_id}/development-impact")
def assess_development_impact(property_id: int, db: Session = Depends(get_db)):
    """
    Assess impact of nearby developments

    Returns impact score and analysis
    """
    service = PropertyResearchService(db)
    result = service.assess_development_impact(property_id)

    if not result['success']:
        raise HTTPException(status_code=404, detail=result.get('error'))

    return result
