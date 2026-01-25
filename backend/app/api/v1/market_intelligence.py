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
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_organization
from app.models.organization import Organization
from app.models.property import Property
from app.models.market_intelligence import MarketIntelligence
from app.models.market_data_lineage import MarketDataLineage
from app.services.market_data_service import MarketDataService
from app.core.config import settings
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/properties/{property_identifier}/market-intelligence/summary")
async def get_market_intelligence_summary(
    property_identifier: str,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get comprehensive market intelligence summary for a property.
    
    Aggregates data from:
    - Demographics
    - Location Intelligence
    - Economic Indicators
    - ESG Assessment
    - Forecasts
    - Competitive Analysis
    
    Args:
        property_identifier: Property ID (int) or Property Code (str)
    """
    try:
        # Resolve property (scoped to org)
        property_obj = get_property_for_org(db, current_org, property_identifier)
            
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
            
        # Get or create market intelligence record
        mi = get_or_create_market_intelligence(db, property_obj.id)
        
        # Construct response data from existing JSON fields
        # If fields are None, they will return as None, which is fine
        data = {
            "demographics": mi.demographics,
            "location_intelligence": mi.location_intelligence,
            "economic_indicators": mi.economic_indicators,
            "esg_assessment": mi.esg_assessment,
            "forecasts": mi.forecasts,
            "competitive_analysis": mi.competitive_analysis,
            "comparables": mi.comparables,
            "ai_insights": mi.ai_insights,
        }
        
        # Calculate executive summary using the internal helper
        # We need a cap rate for 'your_cap_rate'. 
        # Using a default or fetching from metrics would be ideal, but 0.0 is safe fallback.
        executive_summary_data = calculate_executive_summary(data, your_cap_rate=0.0)
        
        # Merge calculated data into response
        response = {
            "property_id": property_obj.id,
            "property_code": property_obj.property_code,
            **data,
            **executive_summary_data
        }
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market intelligence summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Inline executive intelligence calculations (avoiding import issues)
def calculate_executive_summary(mi_data: Dict[str, Any], your_cap_rate: float = 0.0) -> Dict[str, Any]:
    """Calculate executive-level metrics inline."""
    try:
        # Extract data
        demographics = mi_data.get('demographics')
        location_intel = mi_data.get('location_intelligence')
        esg = mi_data.get('esg_assessment')
        forecasts = mi_data.get('forecasts')
        competitive = mi_data.get('competitive_analysis')

        # Calculate location score (0-10)
        location_score = None
        if location_intel and location_intel.get('data'):
            loc = location_intel['data']
            score = 0.0
            score += (loc.get('walk_score', 0) / 100) * 1.2
            score += (loc.get('bike_score', 0) / 100) * 0.9
            score += (loc.get('transit_score', 0) / 100) * 0.9
            score += (loc.get('school_rating_avg', 5) / 10) * 2.0
            score += ((100 - loc.get('crime_index', 50)) / 100) * 2.0

            # Add demographic boost
            if demographics and demographics.get('data'):
                demo = demographics['data']
                if demo.get('median_household_income', 0) > 60000:
                    score += 0.8
                if demo.get('college_educated_pct', 0) > 30:
                    score += 0.7

            location_score = round(min(score, 10.0), 1)

        # Market cap rate
        market_cap_rate = 0.0
        if competitive and competitive.get('data'):
            market_cap_rate = competitive['data'].get('market_avg_cap_rate', 0.0)

        # Rent growth
        rent_growth = None
        if forecasts and forecasts.get('data'):
            rent_growth = forecasts['data'].get('rent_growth_3yr_cagr')

        # Risk score (0-100, higher = more risk)
        risk_score = 50
        if esg and esg.get('data'):
            esg_score = esg['data'].get('composite_score', {}).get('overall', {}).get('score', 75)
            risk_score = round((100 - esg_score) * 0.3 + 25)  # Simplified

        # Opportunity score (0-100, higher = better)
        opp_score = 50
        if rent_growth and rent_growth > 0:
            opp_score = min(30 + rent_growth * 5, 100)
        if location_score:
            opp_score = min(opp_score + location_score * 2, 100)
        opportunity_score = round(opp_score)

        # Investment recommendation
        net_score = opportunity_score - risk_score
        cap_premium = your_cap_rate - market_cap_rate if market_cap_rate > 0 else 0

        if net_score >= 30:
            action = "BUY"
            confidence = 85
            priority = "HIGH"
            rationale = [f"Strong opportunity ({opportunity_score}/100)", f"Manageable risk ({risk_score}/100)"]
        elif net_score >= 0 and cap_premium >= 0:
            action = "HOLD"
            confidence = 75
            priority = "LOW"
            rationale = ["Performing at/above market", "Balanced risk/reward"]
        elif risk_score >= 70:
            action = "SELL"
            confidence = 80
            priority = "HIGH"
            rationale = [f"High risk ({risk_score}/100)", "Limited upside"]
        else:
            action = "REVIEW"
            confidence = 60
            priority = "MEDIUM"
            rationale = ["Mixed signals - detailed analysis needed"]

        return {
            "location_score": location_score,
            "market_cap_rate": market_cap_rate,
            "rent_growth": rent_growth,
            "risk_score": risk_score,
            "opportunity_score": opportunity_score,
            "investment_recommendation": {
                "action": action,
                "confidence": confidence,
                "priority": priority,
                "rationale": rationale,
                "metrics": {
                    "net_score": net_score,
                    "cap_rate_premium": round(cap_premium, 2)
                }
            },
            "key_findings": [],
            "executive_summary": {
                "headline": f"{action}: {rationale[0]}" if rationale else action,
                "quick_stats": {
                    "location_quality": "Premium" if location_score and location_score >= 8 else "Strong" if location_score and location_score >= 6 else "Average",
                    "growth_potential": "Strong" if rent_growth and rent_growth >= 3 else "Moderate" if rent_growth and rent_growth >= 0 else "Limited",
                    "risk_level": "High Risk" if risk_score >= 70 else "Moderate Risk" if risk_score >= 50 else "Low Risk",
                    "opportunity_level": "Strong" if opportunity_score >= 60 else "Moderate" if opportunity_score >= 40 else "Limited"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error calculating executive summary: {e}")
        return {
            "location_score": None,
            "market_cap_rate": 0.0,
            "rent_growth": None,
            "risk_score": 50,
            "opportunity_score": 50,
            "investment_recommendation": {
                "action": "REVIEW",
                "confidence": 0,
                "priority": "HIGH",
                "rationale": ["Error - manual review required"],
                "metrics": {}
            },
            "key_findings": [],
            "executive_summary": {"headline": "Data insufficient", "quick_stats": {}}
        }


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


def get_property_for_org(
    db: Session,
    current_org: Organization,
    property_identifier: str
) -> Optional[Property]:
    """Resolve property by code or id within the current organization."""
    query = Property.filter_by_org(db.query(Property), current_org.id)
    if property_identifier.isdigit():
        return query.filter(Property.id == int(property_identifier)).first()
    return query.filter(Property.property_code == property_identifier).first()


# ========== Demographics ==========

@router.get("/properties/{property_code}/market-intelligence/demographics")
async def get_demographics(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh from Census API"),
    enhanced: bool = Query(True, description="Include supplementary data sources"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get demographics data for a property.

    Returns Census ACS 5-year data (automatically detects latest vintage) including:
    - Population
    - Median household income
    - Median home value
    - Median rent
    - Unemployment rate
    - Education levels
    - Housing units breakdown

    With enhanced=True (default), also includes:
    - Recent population estimates (Census PEP - more current than ACS5)
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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

                latitude = geocode_result['data']['latitude']
                longitude = geocode_result['data']['longitude']
                property_obj.latitude = latitude
                property_obj.longitude = longitude
            else:
                latitude = property_obj.latitude
                longitude = property_obj.longitude

            # Fetch demographics (enhanced or basic)
            service = get_market_data_service(db)
            if enhanced:
                demographics = service.fetch_enhanced_demographics(latitude, longitude)
            else:
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
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
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
        property_obj = get_property_for_org(db, current_org, property_code)
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
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
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
        property_obj = get_property_for_org(db, current_org, property_code)
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

            # Resolve coordinates (prefer stored values)
            latitude = getattr(property_obj, 'latitude', None)
            longitude = getattr(property_obj, 'longitude', None)

            if not latitude or not longitude:
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state}, {property_obj.zip_code}"
                geocoded = market_data_service.geocode_address(full_address)

                if not geocoded:
                    raise HTTPException(status_code=400, detail="Could not geocode property address")

                latitude = geocoded['data']['latitude']
                longitude = geocoded['data']['longitude']
                property_obj.latitude = latitude
                property_obj.longitude = longitude

            # Fetch location intelligence (cache-bust on explicit refresh)
            cache_bust = datetime.utcnow().isoformat() if refresh else None
            location_intel = market_data_service.fetch_location_intelligence(
                latitude,
                longitude,
                cache_bust=cache_bust
            )

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
                if mi.location_intelligence:
                    mi.refresh_status = 'stale'
                    db.commit()
                    db.refresh(mi)
                    return {
                        "property_code": property_code,
                        "location_intelligence": mi.location_intelligence,
                        "last_refreshed": mi.last_refreshed_at
                    }
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


# ========== ESG Assessment ==========

@router.get("/properties/{property_code}/market-intelligence/esg", response_model=None)
async def get_esg_assessment(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh ESG assessment"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get ESG (Environmental, Social, Governance) assessment for a property.

    Includes:
    - Environmental risk (flood, wildfire, earthquake, climate, energy efficiency)
    - Social risk (crime, schools, inequality, diversity, health)
    - Governance risk (zoning, permits, taxes, legal issues)
    - Composite ESG score and grade

    Args:
        property_code: Property code (e.g., ESP001)
        refresh: Force refresh ESG assessment
        db: Database session

    Returns:
        ESG assessment with composite score and grade
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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
        if refresh or not mi.esg_assessment:
            # Get market data service
            market_data_service = get_market_data_service(db)

            # Resolve coordinates (prefer stored values)
            latitude = getattr(property_obj, 'latitude', None)
            longitude = getattr(property_obj, 'longitude', None)

            if not latitude or not longitude:
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state}, {property_obj.zip_code}"
                geocoded = market_data_service.geocode_address(full_address)

                if not geocoded:
                    raise HTTPException(status_code=400, detail="Could not geocode property address")

                latitude = geocoded['data']['latitude']
                longitude = geocoded['data']['longitude']
                property_obj.latitude = latitude
                property_obj.longitude = longitude

            # Prepare property data for ESG assessment
            property_data = {
                'property_code': property_code,
                'property_type': property_obj.property_type,
                'year_built': getattr(property_obj, 'year_built', 2000) # Default to 2000 if not set
            }

            # Fetch ESG assessment
            esg_assessment = market_data_service.fetch_esg_assessment(
                latitude,
                longitude,
                property_data
            )

            if esg_assessment:
                mi.esg_assessment = esg_assessment
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()
                db.refresh(mi)

                # Log to lineage table
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source=esg_assessment['lineage']['source'],
                    data_category='esg',
                    data_vintage=esg_assessment['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=esg_assessment['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=esg_assessment['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            elif mi.esg_assessment:
                # If fetch failed but we have data, keep existing
                logger.warning(f"Failed to refresh ESG data for {property_code}, using cached data")
            else:
                # No data and fetch failed - return empty structure to avoid frontend crash
                logger.error(f"Failed to fetch initial ESG data for {property_code}")
                # Don't raise 500, return empty/pending state
                empty_assessment = {
                    "environmental": {"composite_score": 0}, 
                    "social": {"composite_score": 0}, 
                    "governance": {"composite_score": 0},
                    "composite_esg_score": 0,
                    "esg_grade": "Pending"
                }
                mi.esg_assessment = empty_assessment
                db.commit()

        return {
            "property_code": property_code,
            "esg_assessment": mi.esg_assessment,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ESG assessment for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Predictive Forecasts ==========

@router.get("/properties/{property_code}/market-intelligence/forecasts", response_model=None)
async def get_forecasts(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh forecasts"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get predictive forecasts for a property.

    Includes 12-month projections for:
    - Rent growth
    - Occupancy rates
    - Cap rates
    - Property value

    Each forecast includes confidence intervals and model accuracy metrics.

    Args:
        property_code: Property code (e.g., ESP001)
        refresh: Force regenerate forecasts
        db: Database session

    Returns:
        Forecast data with 12-month projections
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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

        # Check if we need to generate new forecasts
        if refresh or not mi.forecasts:
            # Get market data service
            market_data_service = get_market_data_service(db)

            # Fetch latest financial metrics
            latest_metrics = db.query(FinancialMetrics).join(FinancialPeriod).filter(
                FinancialMetrics.property_id == property_obj.id
            ).order_by(FinancialPeriod.period_end_date.desc()).first()

            # Prepare property data for forecasting
            avg_rent = 1500  # Default fallback
            if latest_metrics and latest_metrics.total_monthly_rent and latest_metrics.occupied_units:
                avg_rent = float(latest_metrics.total_monthly_rent / latest_metrics.occupied_units)
            
            occupancy_rate = 95.0 # Default fallback
            if latest_metrics and latest_metrics.occupancy_rate:
                occupancy_rate = float(latest_metrics.occupancy_rate)

            noi = 500000 # Default fallback
            if latest_metrics and latest_metrics.net_operating_income:
                # Annualize if monthly
                noi = float(latest_metrics.net_operating_income) * 12

            market_value = 10000000 # Default fallback
            if property_obj.purchase_price:
                 market_value = float(property_obj.purchase_price)

            property_data = {
                'property_code': property_code,
                'property_id': property_obj.id,
                'avg_rent': avg_rent,
                'occupancy_rate': occupancy_rate,
                'noi': noi,
                'market_value': market_value
            }

            # TODO: Fetch historical data for better forecasting
            historical_data = None
            
            # Use economic indicators if available
            economic_data = mi.economic_indicators

            # Generate forecasts
            forecasts = market_data_service.generate_forecasts(property_data, historical_data, economic_data)

            if forecasts:
                mi.forecasts = forecasts
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()
                db.refresh(mi)

                # Log to lineage table
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source=forecasts['lineage']['source'],
                    data_category='forecasts',
                    data_vintage=forecasts['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=forecasts['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=forecasts['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to generate forecasts")

        return {
            "property_code": property_code,
            "forecasts": mi.forecasts,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating forecasts for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Competitive Analysis ==========

@router.get("/properties/{property_code}/market-intelligence/competitive", response_model=None)
async def get_competitive_analysis(
    property_code: str,
    refresh: bool = Query(False, description="Force refresh competitive analysis"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get competitive analysis for a property within its submarket.

    Includes:
    - Submarket position (rent, occupancy, quality percentiles)
    - Competitive threats
    - Submarket trends
    - Market share analysis

    Args:
        property_code: Property code (e.g., ESP001)
        refresh: Force regenerate competitive analysis
        db: Database session

    Returns:
        Competitive positioning data
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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

        # Check if we need to generate new competitive analysis
        if refresh or not mi.competitive_analysis:
            # Get market data service
            market_data_service = get_market_data_service(db)

            # Fetch latest financial metrics
            latest_metrics = db.query(FinancialMetrics).join(FinancialPeriod).filter(
                FinancialMetrics.property_id == property_obj.id
            ).order_by(FinancialPeriod.period_end_date.desc()).first()

            # Prepare property data
            avg_rent = 1500
            avg_rent_psf = None
            if latest_metrics and latest_metrics.total_monthly_rent and latest_metrics.occupied_units:
                avg_rent = float(latest_metrics.total_monthly_rent / latest_metrics.occupied_units)
            if latest_metrics and latest_metrics.avg_rent_per_sqft:
                avg_rent_psf = float(latest_metrics.avg_rent_per_sqft)
            elif latest_metrics and latest_metrics.total_monthly_rent and latest_metrics.occupied_sqft:
                denom = float(latest_metrics.occupied_sqft)
                if denom > 0:
                    avg_rent_psf = float(latest_metrics.total_monthly_rent) / denom
            
            occupancy_rate = 95.0
            if latest_metrics and latest_metrics.occupancy_rate:
                occupancy_rate = float(latest_metrics.occupancy_rate)
            
            total_units = 100
            if latest_metrics and latest_metrics.total_units:
                total_units = latest_metrics.total_units
            elif hasattr(property_obj, 'total_units'):
                 total_units = property_obj.total_units

            # Get property coordinates
            latitude = getattr(property_obj, 'latitude', None)
            longitude = getattr(property_obj, 'longitude', None)
            
            if not latitude or not longitude:
                # Attempt to geocode if coordinates missing
                service = get_market_data_service(db)
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state} {property_obj.zip_code}"
                geocode_result = service.geocode_address(full_address)
                if geocode_result:
                    latitude = geocode_result['data']['latitude']
                    longitude = geocode_result['data']['longitude']
                    property_obj.latitude = latitude
                    property_obj.longitude = longitude

            # Open-data benchmarks (Census) if available
            open_data = {}
            if mi.demographics and isinstance(mi.demographics, dict):
                demo = mi.demographics.get('data') or {}
                open_data = {
                    'acs_median_gross_rent': demo.get('median_gross_rent'),
                    'acs_median_household_income': demo.get('median_household_income'),
                    'acs_population': demo.get('population'),
                    'acs_unemployment_rate': demo.get('unemployment_rate')
                }

            property_data = {
                'property_id': property_obj.id,
                'organization_id': current_org.id,
                'property_code': property_code,
                'avg_rent': avg_rent,
                'avg_rent_psf': avg_rent_psf,
                'occupancy_rate': occupancy_rate,
                'total_units': total_units,
                'property_type': property_obj.property_type,
                'submarket': property_obj.city,
                'city': property_obj.city,
                'state': property_obj.state,
                'latitude': float(latitude) if latitude is not None else None,
                'longitude': float(longitude) if longitude is not None else None,
                'open_data': open_data
            }

            # TODO: Fetch submarket data from external API or database
            submarket_data = None

            # Analyze competitive position
            competitive = market_data_service.analyze_competitive_position(
                property_data,
                submarket_data,
                cache_bust=datetime.utcnow().isoformat()
            )

            if competitive:
                # Generate LLM narrative for competitive analysis (best-effort)
                try:
                    existing_narrative = None
                    if isinstance(competitive, dict):
                        existing_narrative = (competitive.get('data') or {}).get('llm_narrative')
                    if refresh or not existing_narrative:
                        from app.services.market_intelligence_ai_service import get_market_intelligence_ai_service
                        ai_service = get_market_intelligence_ai_service()

                        # Build minimal market_data payload for prompt
                        loc_prompt = {}
                        if mi.location_intelligence and isinstance(mi.location_intelligence, dict):
                            loc_data = mi.location_intelligence.get('data') or {}
                            amenities = loc_data.get('amenities') or {}
                            loc_prompt = {
                                'walk_score': loc_data.get('walk_score'),
                                'nearby_restaurants': amenities.get('restaurants_1mi'),
                                'nearby_grocery': amenities.get('grocery_stores_1mi')
                            }

                        market_data = {
                            'property_code': property_code,
                            'competitive_analysis': competitive,
                            'location_intelligence': {'data': loc_prompt}
                        }

                        property_metrics = {
                            'current_rent_psf': property_data.get('avg_rent_psf') or property_data.get('avg_rent'),
                            'current_occupancy': property_data.get('occupancy_rate')
                        }

                        llm_narrative = await ai_service._generate_competitive_analysis_with_llm(
                            market_data,
                            property_metrics
                        )
                        if llm_narrative:
                            competitive.setdefault('data', {})['llm_narrative'] = llm_narrative
                except Exception as llm_err:
                    logger.warning(f"Competitive narrative generation skipped: {llm_err}")

                mi.competitive_analysis = competitive
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()
                db.refresh(mi)

                # Log to lineage table
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source=competitive['lineage']['source'],
                    data_category='competitive',
                    data_vintage=competitive['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=competitive['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=competitive['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to analyze competitive position")

        return {
            "property_code": property_code,
            "competitive_analysis": mi.competitive_analysis,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing competitive position for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== AI Insights ==========

@router.get("/properties/{property_code}/market-intelligence/insights", response_model=None)
async def get_ai_insights(
    property_code: str,
    refresh: bool = Query(False, description="Force regenerate AI insights"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get AI-powered insights and recommendations for a property.

    Synthesizes all market intelligence data to generate:
    - SWOT analysis (Strengths, Weaknesses, Opportunities, Threats)
    - Investment recommendation (BUY/HOLD/SELL)
    - Risk assessment narrative
    - Value-creation opportunities
    - Market trend synthesis

    Args:
        property_code: Property code (e.g., ESP001)
        refresh: Force regenerate AI insights
        db: Database session

    Returns:
        AI-generated insights and recommendations
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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

        # Check if we need to generate new AI insights
        if refresh or not mi.ai_insights:
            # Get market data service
            market_data_service = get_market_data_service(db)

            # Prepare property data
            property_data = {
                'property_code': property_code,
                'property_type': property_obj.property_type,
                'year_built': property_obj.year_built if hasattr(property_obj, 'year_built') else None,
                'avg_rent': 1500,  # TODO: Get from actual property metrics
                'occupancy_rate': 95.0,  # TODO: Get from actual property metrics
                'noi': 500000  # TODO: Get from financial data
            }

            # Gather all market intelligence data
            market_intelligence = {
                'demographics': mi.demographics,
                'economic_indicators': mi.economic_indicators,
                'location_intelligence': mi.location_intelligence,
                'esg_assessment': mi.esg_assessment,
                'forecasts': mi.forecasts,
                'competitive_analysis': mi.competitive_analysis
            }

            # Generate AI insights
            ai_insights = await market_data_service.generate_ai_insights(property_data, market_intelligence)

            if ai_insights:
                ai_insights['property_code'] = property_code
                try:
                    embeddings_meta = market_data_service.generate_ai_embeddings(ai_insights)
                    if embeddings_meta:
                        ai_insights['embeddings'] = embeddings_meta
                except Exception as emb_err:
                    logger.debug(f"AI embedding generation skipped: {emb_err}")
                mi.ai_insights = ai_insights
                mi.last_refreshed_at = datetime.utcnow()
                mi.refresh_status = 'success'
                db.commit()
                db.refresh(mi)

                # Log to lineage table
                lineage = MarketDataLineage(
                    property_id=property_obj.id,
                    data_source=ai_insights['lineage']['source'],
                    data_category='insights',
                    data_vintage=ai_insights['lineage']['vintage'],
                    fetched_at=datetime.utcnow(),
                    confidence_score=ai_insights['lineage']['confidence'],
                    fetch_status='success',
                    records_fetched=1,
                    extra_metadata=ai_insights['lineage']['extra_metadata']
                )
                db.add(lineage)
                db.commit()
            else:
                raise HTTPException(status_code=500, detail="Failed to generate AI insights")

        return {
            "property_code": property_code,
            "ai_insights": mi.ai_insights,
            "last_refreshed": mi.last_refreshed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI insights for {property_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Complete Market Intelligence ==========

@router.get("/properties/{property_code}/market-intelligence")
async def get_market_intelligence(
    property_code: str,
    include_executive_summary: bool = Query(True, description="Include calculated executive metrics"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
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
    - Executive summary (calculated metrics for C-level decision making)
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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
                "refresh_status": None,
                "executive_summary": None
            }

        # Build base response
        response = {
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

        # Calculate executive summary if requested
        if include_executive_summary:
            try:
                # Fetch property cap rate if available
                your_cap_rate = 0.0
                try:
                    from app.services.metrics_service import calculate_cap_rate
                    cap_rate_result = calculate_cap_rate(db, property_obj.id)
                    if cap_rate_result and 'cap_rate' in cap_rate_result:
                        your_cap_rate = cap_rate_result['cap_rate']
                except Exception as cap_err:
                    logger.warning(f"Could not fetch cap rate for {property_code}: {cap_err}")

                # Generate executive summary using inline function
                executive_summary = calculate_executive_summary(response, your_cap_rate)
                response["executive_summary"] = executive_summary

            except Exception as exec_err:
                logger.error(f"Error generating executive summary: {exec_err}")
                response["executive_summary"] = None

        return response

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
    use_celery: bool = Query(False, description="If true, enqueue refresh via Celery"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Refresh market intelligence data for a property.

    Can refresh specific categories or all categories.
    Runs in background for large refreshes.
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
        if not property_obj:
            raise HTTPException(status_code=404, detail=f"Property {property_code} not found")

        # Default to all categories if none specified
        if not categories:
            categories = [
                'demographics', 'economic', 'location', 'esg',
                'forecasts', 'competitive', 'comparables', 'insights'
            ]

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

        # If async requested, enqueue Celery task and return immediately
        if use_celery:
            try:
                from app.tasks.market_intelligence_tasks import refresh_market_intelligence_task
                task = refresh_market_intelligence_task.delay(property_code=property_code, property_id=property_obj.id)
                return {"status": "queued", "task_id": task.id}
            except Exception as e:
                logger.error(f"Failed to enqueue Celery task: {e} — falling back to sync refresh")

        # Fetch latest financial metrics for real data
        latest_metrics = db.query(FinancialMetrics).join(FinancialPeriod).filter(
            FinancialMetrics.property_id == property_obj.id
        ).order_by(FinancialPeriod.period_end_date.desc()).first()

        # Default values (fallback)
        avg_rent = 1500.0
        avg_rent_psf = None
        occupancy_rate = 95.0
        noi = 500000.0
        total_units = getattr(property_obj, 'total_units', 100)

        if latest_metrics:
            if latest_metrics.total_monthly_rent and latest_metrics.occupied_units:
                 avg_rent = float(latest_metrics.total_monthly_rent / latest_metrics.occupied_units)
            if latest_metrics.occupancy_rate:
                occupancy_rate = float(latest_metrics.occupancy_rate)
            if latest_metrics.net_operating_income:
                noi = float(latest_metrics.net_operating_income) * 12 # Annualize
            if latest_metrics.total_units:
                total_units = latest_metrics.total_units
            if latest_metrics.avg_rent_per_sqft:
                avg_rent_psf = float(latest_metrics.avg_rent_per_sqft)
            elif latest_metrics.total_monthly_rent and latest_metrics.occupied_sqft:
                denom = float(latest_metrics.occupied_sqft)
                if denom > 0:
                    avg_rent_psf = float(latest_metrics.total_monthly_rent) / denom

        # Attempt geocoding once for reuse (prefer stored coordinates)
        latitude = getattr(property_obj, 'latitude', None)
        longitude = getattr(property_obj, 'longitude', None)
        geocoded = None
        if (not latitude or not longitude) and property_obj.address:
            try:
                full_address = f"{property_obj.address}, {property_obj.city}, {property_obj.state}, {property_obj.zip_code}"
                geocoded = service.geocode_address(full_address)
            except Exception as geo_err:
                logger.warning(f"Geocoding failed for {property_code}: {geo_err}")

        if geocoded and geocoded.get('data'):
            latitude = geocoded['data'].get('latitude')
            longitude = geocoded['data'].get('longitude')
            if latitude and longitude:
                property_obj.latitude = latitude
                property_obj.longitude = longitude
        
        # Open-data benchmarks (Census) if available
        open_data = {}
        if mi.demographics and isinstance(mi.demographics, dict):
            demo = mi.demographics.get('data') or {}
            open_data = {
                'acs_median_gross_rent': demo.get('median_gross_rent'),
                'acs_median_household_income': demo.get('median_household_income'),
                'acs_population': demo.get('population'),
                'acs_unemployment_rate': demo.get('unemployment_rate')
            }

        # Base property data for all services
        base_property_data = {
            'property_id': property_obj.id,
            'organization_id': current_org.id,
            'property_code': property_code,
            'property_type': property_obj.property_type,
            'year_built': getattr(property_obj, 'year_built', None),
            'city': property_obj.city,
            'state': property_obj.state,
            'avg_rent': avg_rent,
            'avg_rent_psf': avg_rent_psf,
            'occupancy_rate': occupancy_rate,
            'noi': noi,
            'market_value': getattr(property_obj, 'market_value', 10000000), # Fallback if not tracked
            'total_units': total_units,
            'latitude': latitude,
            'longitude': longitude,
            'open_data': open_data
        }

        # Refresh demographics
        if 'demographics' in categories:
            try:
                demographics = None
                if latitude and longitude:
                    demographics = service.fetch_enhanced_demographics(latitude, longitude)
                
                if demographics:
                    mi.demographics = demographics
                    refreshed.append('demographics')
                else:
                    logger.warning(f"No demographics data found for {property_code}")
                    # No sample data fallback
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
                else:
                     logger.warning(f"No economic data available")
                     # No sample data fallback
            except Exception as e:
                logger.error(f"Failed to refresh economic indicators: {e}")
                errors.append({'category': 'economic', 'error': str(e)})

        # Refresh location intelligence
        if 'location' in categories:
            try:
                location_intel = None
                if latitude and longitude:
                    location_intel = service.fetch_location_intelligence(
                        latitude,
                        longitude,
                        cache_bust=datetime.utcnow().isoformat()
                    )
                
                if location_intel:
                    mi.location_intelligence = location_intel
                    refreshed.append('location')
                else:
                    logger.warning(f"No location intelligence found for {property_code}")
                    if mi.location_intelligence:
                        # Keep existing data when refresh fails
                        refreshed.append('location')
            except Exception as e:
                logger.error(f"Failed to refresh location intelligence: {e}")
                errors.append({'category': 'location', 'error': str(e)})

        # Refresh ESG assessment
        if 'esg' in categories:
            try:
                esg_assessment = None
                if latitude and longitude:
                    prop_meta = {
                        'property_code': property_code,
                        'property_type': property_obj.property_type,
                        'year_built': getattr(property_obj, 'year_built', None)
                    }
                    esg_assessment = service.fetch_esg_assessment(latitude, longitude, prop_meta)
                
                if esg_assessment:
                    mi.esg_assessment = esg_assessment
                    refreshed.append('esg')
                else:
                     logger.warning(f"No ESG assessment found for {property_code}")
                     # No sample data fallback
            except Exception as e:
                logger.error(f"Failed to refresh ESG assessment: {e}")
                errors.append({'category': 'esg', 'error': str(e)})

        # Refresh forecasts
        if 'forecasts' in categories:
            try:
                forecasts = service.generate_forecasts(base_property_data, None)
                if forecasts:
                    mi.forecasts = forecasts
                    refreshed.append('forecasts')
                else:
                    logger.warning(f"Could not generate forecasts for {property_code}")
                    # No sample data fallback
            except Exception as e:
                logger.error(f"Failed to refresh forecasts: {e}")
                errors.append({'category': 'forecasts', 'error': str(e)})

        # Refresh competitive analysis
        if 'competitive' in categories:
            try:
                competitive = service.analyze_competitive_position(
                    base_property_data,
                    None,
                    cache_bust=datetime.utcnow().isoformat()
                )
                if competitive:
                    # Best-effort LLM narrative
                    try:
                        from app.services.market_intelligence_ai_service import get_market_intelligence_ai_service
                        ai_service = get_market_intelligence_ai_service()
                        loc_prompt = {}
                        if mi.location_intelligence and isinstance(mi.location_intelligence, dict):
                            loc_data = mi.location_intelligence.get('data') or {}
                            amenities = loc_data.get('amenities') or {}
                            loc_prompt = {
                                'walk_score': loc_data.get('walk_score'),
                                'nearby_restaurants': amenities.get('restaurants_1mi'),
                                'nearby_grocery': amenities.get('grocery_stores_1mi')
                            }
                        market_data = {
                            'property_code': property_code,
                            'competitive_analysis': competitive,
                            'location_intelligence': {'data': loc_prompt}
                        }
                        property_metrics = {
                            'current_rent_psf': base_property_data.get('avg_rent_psf') or base_property_data.get('avg_rent'),
                            'current_occupancy': base_property_data.get('occupancy_rate')
                        }
                        llm_narrative = await ai_service._generate_competitive_analysis_with_llm(
                            market_data,
                            property_metrics
                        )
                        if llm_narrative:
                            competitive.setdefault('data', {})['llm_narrative'] = llm_narrative
                    except Exception as llm_err:
                        logger.warning(f"Competitive narrative generation skipped: {llm_err}")

                    mi.competitive_analysis = competitive
                    refreshed.append('competitive')
                else:
                    logger.warning(f"Could not generate competitive analysis for {property_code}")
                    # No sample data fallback
            except Exception as e:
                logger.error(f"Failed to refresh competitive analysis: {e}")
                errors.append({'category': 'competitive', 'error': str(e)})

        # Refresh AI insights
        if 'insights' in categories:
            try:
                market_intelligence_data = {
                    'demographics': mi.demographics,
                    'economic_indicators': mi.economic_indicators,
                    'location_intelligence': mi.location_intelligence,
                    'esg_assessment': mi.esg_assessment,
                    'forecasts': mi.forecasts,
                    'competitive_analysis': mi.competitive_analysis
                }
                ai_insights = await service.generate_ai_insights(base_property_data, market_intelligence_data)
                
                if ai_insights:
                    ai_insights['property_code'] = property_code
                    try:
                        embeddings_meta = service.generate_ai_embeddings(ai_insights)
                        if embeddings_meta:
                            ai_insights['embeddings'] = embeddings_meta
                    except Exception as emb_err:
                        logger.debug(f"AI embedding generation skipped: {emb_err}")
                    mi.ai_insights = ai_insights
                    refreshed.append('insights')
                else:
                    logger.warning(f"Could not generate AI insights for {property_code}")
                    # No sample data fallback
            except Exception as e:
                logger.error(f"Failed to refresh AI insights: {e}")
                errors.append({'category': 'insights', 'error': str(e)})

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
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get data lineage/audit trail for market intelligence.

    Shows all data pulls with source, vintage, confidence, and status.
    """
    try:
        # Get property
        property_obj = get_property_for_org(db, current_org, property_code)
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
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get statistics about market intelligence coverage.

    Returns counts of properties with various data types.
    """
    try:
        total_properties = db.query(Property).filter(
            Property.status == 'active',
            Property.organization_id == current_org.id
        ).count()

        properties_with_mi = db.query(MarketIntelligence).join(
            Property, MarketIntelligence.property_id == Property.id
        ).filter(Property.organization_id == current_org.id).count()

        # Count by data type (non-null)
        demographics_count = db.query(MarketIntelligence).join(
            Property, MarketIntelligence.property_id == Property.id
        ).filter(
            Property.organization_id == current_org.id,
            MarketIntelligence.demographics.isnot(None)
        ).count()

        economic_count = db.query(MarketIntelligence).join(
            Property, MarketIntelligence.property_id == Property.id
        ).filter(
            Property.organization_id == current_org.id,
            MarketIntelligence.economic_indicators.isnot(None)
        ).count()

        # Data pulls in last 30 days
        from datetime import timedelta
        recent_pulls = db.query(MarketDataLineage).join(
            Property, MarketDataLineage.property_id == Property.id
        ).filter(
            Property.organization_id == current_org.id,
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
