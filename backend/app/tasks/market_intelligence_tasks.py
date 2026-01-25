"""
Celery tasks for Market Intelligence ingestion and refresh.
Leverages existing market_data_service routines; uses sample generators as fallback.
"""

from celery import shared_task
from typing import Optional
from app.db.database import SessionLocal
from app.models.property import Property
from app.models.market_intelligence import MarketIntelligence
from app.services.market_data_service import MarketDataService
from app.api.v1.market_intelligence import get_or_create_market_intelligence
import logging

logger = logging.getLogger(__name__)


def _service(db):
    return MarketDataService(db=db)


@shared_task(name="market_intelligence.refresh_all")
def refresh_market_intelligence_task(property_code: str, property_id: Optional[int] = None):
    """
    Refresh all market intelligence categories for a property (async).
    """
    db = SessionLocal()
    try:
        if property_id is not None:
            prop = db.query(Property).filter(Property.id == property_id).first()
        else:
            prop = db.query(Property).filter(Property.property_code == property_code).first()
        if not prop:
            logger.error(f"[MI] Property {property_code} not found")
            return {"status": "error", "error": "property_not_found"}

        property_code = prop.property_code

        mi = get_or_create_market_intelligence(db, prop.id)
        service = _service(db)

        results = {}
        # Geocode once (prefer stored coordinates)
        latitude = getattr(prop, 'latitude', None)
        longitude = getattr(prop, 'longitude', None)
        try:
            if (not latitude or not longitude) and prop.address:
                geo = service.geocode_address(f"{prop.address}, {prop.city}, {prop.state}, {prop.zip_code}")
                if geo and geo.get('data'):
                    latitude = geo['data'].get('latitude')
                    longitude = geo['data'].get('longitude')
                    if latitude and longitude:
                        prop.latitude = latitude
                        prop.longitude = longitude
        except Exception as geo_err:
            logger.warning(f"[MI] Geocoding failed for {property_code}: {geo_err}")

        # Build property meta for downstream calculations
        prop_meta_base = {
            'property_code': property_code,
            'property_id': prop.id,
            'organization_id': getattr(prop, 'organization_id', None),
            'property_type': prop.property_type,
            'year_built': getattr(prop, 'year_built', None),
            'avg_rent': 1500,
            'occupancy_rate': 95.0,
            'noi': 500000,
            'market_value': 10000000,
            'total_units': getattr(prop, 'total_units', 100),
            'submarket': prop.city,
            'city': prop.city,
            'state': prop.state,
            'latitude': latitude,
            'longitude': longitude,
        }

        # Demographics
        try:
            demo = service.fetch_enhanced_demographics(latitude, longitude) if latitude and longitude else None
            mi.demographics = demo or service.generate_sample_demographics(property_code)
            results['demographics'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] demographics failed: {e}")
            results['demographics'] = f"error:{e}"

        # Economic
        try:
            econ = service.fetch_fred_economic_indicators()
            mi.economic_indicators = econ or service.generate_sample_economic()
            results['economic'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] economic failed: {e}")
            results['economic'] = f"error:{e}"

        # Location
        try:
            loc = service.fetch_location_intelligence(latitude, longitude) if latitude and longitude else None
            mi.location_intelligence = loc or service.generate_sample_location(latitude or 37.77, longitude or -122.42)
            results['location'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] location failed: {e}")
            results['location'] = f"error:{e}"

        # ESG
        try:
            esg = None
            if latitude and longitude:
                meta = {'property_code': property_code, 'property_type': prop.property_type, 'year_built': getattr(prop, 'year_built', None)}
                esg = service.fetch_esg_assessment(latitude, longitude, meta)
            mi.esg_assessment = esg or service.generate_sample_esg()
            results['esg'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] esg failed: {e}")
            results['esg'] = f"error:{e}"

        # Forecasts
        try:
            forecasts = service.generate_forecasts(prop_meta_base, None, mi.economic_indicators or {})
            mi.forecasts = forecasts or service.generate_sample_forecasts()
            results['forecasts'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] forecasts failed: {e}")
            results['forecasts'] = f"error:{e}"

        # Competitive
        try:
            comp = service.analyze_competitive_position(
                prop_meta_base,
                None,
                cache_bust=datetime.utcnow().isoformat()
            )
            mi.competitive_analysis = comp or service.generate_sample_competitive()
            results['competitive'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] competitive failed: {e}")
            results['competitive'] = f"error:{e}"

        # AI Insights + embeddings
        try:
            intel = {
                'demographics': mi.demographics,
                'economic_indicators': mi.economic_indicators,
                'location_intelligence': mi.location_intelligence,
                'esg_assessment': mi.esg_assessment,
                'forecasts': mi.forecasts,
                'competitive_analysis': mi.competitive_analysis,
            }
            insights = service.generate_ai_insights(prop_meta_base, intel)
            if not insights:
                insights = service.generate_sample_ai_insights()
            insights['property_code'] = property_code
            embeddings = service.generate_ai_embeddings(insights)
            if embeddings:
                insights['embeddings'] = embeddings
            mi.ai_insights = insights
            results['insights'] = 'ok'
        except Exception as e:
            logger.error(f"[MI] ai_insights failed: {e}")
            results['insights'] = f"error:{e}"

        mi.refresh_status = 'success' if all(v == 'ok' for v in results.values()) else 'partial'
        db.commit()
        return {"status": mi.refresh_status, "results": results}
    except Exception as e:
        logger.error(f"[MI] refresh task failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
