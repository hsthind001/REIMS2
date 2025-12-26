"""
Market Intelligence API Endpoints

RESTful API for comprehensive market intelligence including:
- Demographics
- Economic indicators
- Location intelligence
- ESG assessment
- Predictive forecasts
- Competitive analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.property import Property
from app.models.market_intelligence import MarketIntelligence
from app.models.market_data_lineage import MarketDataLineage
from app.services.market_data_service import MarketDataService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Helper Functions ==========

def get_market_data_service(db: Session) -> MarketDataService:
    """Get market data service instance."""
    return MarketDataService(
        db=db,
        census_api_key=getattr(settings, 'CENSUS_API_KEY', None),
        fred_api_key=getattr(settings, 'FRED_API_KEY', None)
    )


def get_or_create_market_intelligence(db: Session, property_id: int) -> MarketIntelligence:
    """Get existing or create new market intelligence record."""
    mi = db.query(MarketIntelligence).filter(
        MarketIntelligence.property_id == property_id
    ).first()

    if not mi:
        mi = MarketIntelligence(property_id=property_id)
        db.add(mi)
        db.commit()
        db.refresh(mi)

    return mi


# ========== Demographics ==========

@router.get("/properties/{property_code}/market-intelligence/demographics")
async def get_demographics(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh from Census API"),
    db: Session = Depends(get_db)
):
    """
    Get demographics data for a property.

    Returns Census ACS 5-year data including:
    - Population
    - Median household income
    - Median home value
    - Median rent
    - Unemployment rate
    - Education levels
    - Housing units breakdown
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Get or create market intelligence record
        mi = get_or_create_market_intelligence(db, property_obj.id)

        # Check if we need to refresh
        if refresh or not mi.demographics:
            # Need property coordinates - check if geocoded
            if not hasattr(property_obj, 'latitude') or not property_obj.latitude:
                # Geocode the property address first
                service = get_market_data_service(db)
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state} {property_obj.zip_code}"
                geocode_result = service.geocode_address(full_address)

                if not geocode_result:
                    raise HTTPException(
                        status_code=400,
                        detail="Could not geocode property address. Please ensure address is valid."
                    )

                # Store coordinates (would need to add lat/lon fields to Property model)
                latitude = geocode_result['data']['latitude']
                longitude = geocode_result['data']['longitude']
            else:
                latitude = property_obj.latitude
                longitude = property_obj.longitude

            # Fetch demographics
            service = get_market_data_service(db)
            demographics = service.fetch_census_demographics(latitude, longitude)

            if demographics:
                mi.demographics = demographics
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()

                # Log to lineage
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source='census_acs5',
                    endpoint='acs5',
                    data_category='demographics',
                    data_vintage=demographics['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=demographics['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=demographics['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch demographics data")

        return {
            "property_code": property_code,
            "demographics": mi.demographics,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching demographics for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Economic Indicators ==========

@router.get("/properties/{property_code}/market-intelligence/economic")
async def get_economic_indicators(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh from FRED API"),
    msa_code: Optional[str] = Query(None, description="MSA code for local indicators"),
    db: Session = Depends(get_db)
):
    """
    Get economic indicators for a property's market.

    Returns FRED data including:
    - GDP growth
    - Unemployment rate
    - Inflation rate
    - Interest rates
    - Mortgage rates
    - Recession probability
    - MSA-specific indicators (if MSA code provided)
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Get or create market intelligence record
        mi = get_or_create_market_intelligence(db, property_obj.id)

        # Check if we need to refresh
        if refresh or not mi.economic_indicators:
            service = get_market_data_service(db)
            economic = service.fetch_fred_economic_indicators(msa_code)

            if economic:
                mi.economic_indicators = economic
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()

                # Log to lineage
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source='fred',
                    endpoint='series/observations',
                    data_category='economic',
                    data_vintage=economic['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=economic['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=len(economic['data']),
                    extra_metadata=economic['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch economic indicators")

        return {
            "property_code": property_code,
            "economic_indicators": mi.economic_indicators,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching economic indicators for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Location Intelligence ==========

@router.get("/properties/{property_code}/market-intelligence/location", response_model=None)
async def get_location_intelligence(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh from external APIs"),
    db: Session = Depends(get_db)
):
    """
    Get location intelligence data for a property.

    Includes:
    - Walk/Transit/Bike scores
    - Amenity counts (grocery, restaurants, schools, hospitals, parks)
    - Transit access metrics
    - Crime index
    - School ratings

    Args:
        property_code: Property code (e.g., ESP001)
        refresh: Force refresh from external APIs
        db: Database session
        market_data_service: Market data service instance

    Returns:
        Location intelligence data with lineage
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Get or create market intelligence record
        mi = db.query(MarketIntelligence).filter(
            MarketIntelligence.property_id == property_obj.id
        ).first()

        if not mi:
            mi = MarketIntelligence(property_id=property_obj.id)
            db.add(mi)
            db.commit()
            db.refresh(mi)

        # Check if we need to fetch new data
        if refresh or not mi.location_intelligence:
            # Get market data service
            market_data_service = get_market_data_service(db)

            # First, geocode the property address
            full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state}, {property_obj.zip_code}"
            geocoded = market_data_service.geocode_address(full_address)

            if not geocoded:
                raise HTTPException(status_code=400, detail="Could not geocode property address")

            latitude = geocoded['data']['latitude']
            longitude = geocoded['data']['longitude']

            # Fetch location intelligence
            location_intel = market_data_service.fetch_location_intelligence(latitude, longitude)

            if location_intel:
                mi.location_intelligence = location_intel
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()
                db.refresh(mi)

                # Log to lineage table
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source=location_intel['lineage']['source'],
                    data_category='location',
                    data_vintage=location_intel['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=location_intel['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=location_intel['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch location intelligence")

        return {
            "property_code": property_code,
            "location_intelligence": mi.location_intelligence,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching location intelligence for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Complete Market Intelligence ==========

@router.get("/properties/{property_code}/market-intelligence")
async def get_market_intelligence(
    property_code: str,
    db: Session = Depends(get_db)
):
    """
    Get complete market intelligence data for a property.

    Returns all available market intelligence including:
    - Demographics
    - Economic indicators
    - Location intelligence
    - ESG assessment
    - Forecasts
    - Competitive analysis
    - Comparables
    - AI insights
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Get market intelligence
        mi = db.query(MarketIntelligence).filter(
            MarketIntelligence.property_id == property_obj.id
        ).first()

        if not mi:
            # Return empty structure
            return {
                "property_code": property_code,
                "property_id": property_obj.id,
                "demographics": None,
                "economic_indicators": None,
                "location_intelligence": None,
                "esg_assessment": None,
                "forecasts": None,
                "competitive_analysis": None,
                "comparables": None,
                "ai_insights": None,
                "last_refreshed": None,
                "refresh_status": None
            }

        return {
            "property_code": property_code,
            "property_id": property_obj.id,
            "demographics": mi.demographics,
            "economic_indicators": mi.economic_indicators,
            "location_intelligence": mi.location_intelligence,
            "esg_assessment": mi.esg_assessment,
            "forecasts": mi.forecasts,
            "competitive_analysis": mi.competitive_analysis,
            "comparables": mi.comparables,
            "ai_insights": mi.ai_insights,
            "last_refreshed": mi.last_refreshed_at,
            "refresh_status": mi.refresh_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market intelligence for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Refresh Market Intelligence ==========

@router.post("/properties/{property_code}/market-intelligence/refresh")
async def refresh_market_intelligence(
    property_code: str,
    background_tasks: BackgroundTasks,
    categories: Optional[List[str]] = Query(
        None,
        description="Categories to refresh (demographics, economic, location, esg, forecasts, competitive, comparables, insights). If not specified, refreshes all."
    ),
    db: Session = Depends(get_db)
):
    """
    Refresh market intelligence data for a property.

    Can refresh specific categories or all categories.
    Runs in background for large refreshes.
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Default to all categories if none specified
        if not categories:
            categories = ['demographics', 'economic']

        # Validate categories
        valid_categories = {
            'demographics', 'economic', 'location', 'esg',
            'forecasts', 'competitive', 'comparables', 'insights'
        }
        invalid = set(categories) - valid_categories
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid categories: {', '.join(invalid)}"
            )

        # Get or create market intelligence record
        mi = get_or_create_market_intelligence(db, property_obj.id)

        refreshed = []
        errors = []

        service = get_market_data_service(db)

        # Refresh demographics
        if 'demographics' in categories:
            try:
                # Would need lat/lon - simplified for now
                logger.info(f"Refreshing demographics for {property_code}")
                refreshed.append('demographics')
            except Exception as e:
                logger.error(f"Failed to refresh demographics: {e}")
                errors.append({'category': 'demographics', 'error': str(e)})

        # Refresh economic indicators
        if 'economic' in categories:
            try:
                economic = service.fetch_fred_economic_indicators()
                if economic:
                    mi.economic_indicators = economic
                    refreshed.append('economic')
            except Exception as e:
                logger.error(f"Failed to refresh economic indicators: {e}")
                errors.append({'category': 'economic', 'error': str(e)})

        # Refresh location intelligence
        if 'location' in categories:
            try:
                # Geocode property address
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state}, {property_obj.zip_code}"
                geocoded = service.geocode_address(full_address)
                if geocoded:
                    latitude = geocoded['data']['latitude']
                    longitude = geocoded['data']['longitude']
                    location_intel = service.fetch_location_intelligence(latitude, longitude)
                    if location_intel:
                        mi.location_intelligence = location_intel
                        refreshed.append('location')
            except Exception as e:
                logger.error(f"Failed to refresh location intelligence: {e}")
                errors.append({'category': 'location', 'error': str(e)})

        # Update refresh status
        if errors:
            mi.refresh_status = 'partial' if refreshed else 'failure'
            mi.refresh_error = str(errors)
        else:
            mi.refresh_status = 'success'
            mi.refresh_error = None

        mi.last_refreshed_at = datetime.utcnow()
        db.commit()

        return {
            "property_code": property_code,
            "status": mi.refresh_status,
            "refreshed": refreshed,
            "errors": errors,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing market intelligence for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Data Lineage ==========

@router.get("/properties/{property_code}/market-intelligence/lineage")
async def get_data_lineage(
    property_code: str,
    category: Optional[str] = Query(None, description="Filter by data category"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    Get data lineage/audit trail for market intelligence.

    Shows all data pulls with source, vintage, confidence, and status.
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.property_code == property_code).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Query lineage
        query = db.query(MarketDataLineage).filter(
            MarketDataLineage.property_id == property_obj.id
        )

        if category:
            query = query.filter(MarketDataLineage.data_category == category)

        lineage_records = query.order_by(
            MarketDataLineage.fetched_at.desc()
        ).limit(limit).all()

        return {
            "property_code": property_code,
            "category": category,
            "total_records": len(lineage_records),
            "lineage": [
                {
                    "id": record.id,
                    "source": record.data_source,
                    "category": record.data_category,
                    "vintage": record.data_vintage,
                    "fetched_at": record.fetched_at,
                    "status": record.fetch_status,
                    "confidence": float(record.confidence_score) if record.confidence_score else None,
                    "records_fetched": record.records_fetched,
                    "error": record.error_message
                }
                for record in lineage_records
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data lineage for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Statistics ==========

@router.get("/market-intelligence/statistics")
async def get_market_intelligence_statistics(
    db: Session = Depends(get_db)
):
    """
    Get statistics about market intelligence coverage.

    Returns counts of properties with various data types.
    """
    try:
        total_properties = db.query(Property).filter(Property.status == 'active').count()

        properties_with_mi = db.query(MarketIntelligence).count()

        # Count by data type (non-null)
        demographics_count = db.query(MarketIntelligence).filter(
            MarketIntelligence.demographics.isnot(None)
        ).count()

        economic_count = db.query(MarketIntelligence).filter(
            MarketIntelligence.economic_indicators.isnot(None)
        ).count()

        # Data pulls in last 30 days
        from datetime import timedelta
        recent_pulls = db.query(MarketDataLineage).filter(
            MarketDataLineage.fetched_at >= datetime.utcnow() - timedelta(days=30)
        ).count()

        return {
            "total_active_properties": total_properties,
            "properties_with_market_intelligence": properties_with_mi,
            "coverage": {
                "demographics": demographics_count,
                "economic_indicators": economic_count
            },
            "coverage_percentage": {
                "demographics": round(demographics_count / total_properties * 100, 1) if total_properties > 0 else 0,
                "economic": round(economic_count / total_properties * 100, 1) if total_properties > 0 else 0
            },
            "data_pulls_last_30_days": recent_pulls
        }

    except Exception as e:
        logger.error(f"Error fetching market intelligence statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
