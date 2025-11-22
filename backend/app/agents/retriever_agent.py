"""
M1 Retriever Agent - Research & Data Collection

Searches and scrapes external data sources, summarizes to structured JSON

Data sources:
- Census Bureau API (demographics)
- Bureau of Labor Statistics API (employment)
- Google Places API (nearby businesses)
- Development tracking (building permits, news)
"""
from typing import Dict, List, Optional
from datetime import datetime, date
import httpx
import logging
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.property_research import PropertyResearch  # To be created
from app.core.config import settings

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    M1 Retriever Agent - Autonomous research and data collection

    Capabilities:
    1. Property research (location, zoning, permits)
    2. Demographics (Census Bureau)
    3. Employment statistics (BLS)
    4. Market analysis (nearby businesses)
    5. Development tracking
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    async def conduct_research(self, property_id: int) -> Dict:
        """
        Conduct comprehensive research for a property

        Returns structured JSON with all research data
        """
        logger.info(f"M1 Retriever: Starting research for property {property_id}")

        # Get property
        property = self.db.query(Property).filter(Property.id == property_id).first()
        if not property:
            return {"success": False, "error": "Property not found"}

        # Gather all data
        research_data = {
            "property_id": property_id,
            "research_date": date.today().isoformat(),
            "demographics": await self._get_demographics(property),
            "employment": await self._get_employment_data(property),
            "developments": await self._get_nearby_developments(property),
            "market_analysis": await self._get_market_analysis(property),
            "sources": self._get_sources(),
            "confidence_score": 0.0
        }

        # Calculate confidence based on data availability
        research_data["confidence_score"] = self._calculate_confidence(research_data)

        logger.info(f"M1 Retriever: Research complete. Confidence: {research_data['confidence_score']:.2f}")

        # Store in database
        self._store_research(research_data)

        return {
            "success": True,
            "data": research_data
        }

    async def _get_demographics(self, property: Property) -> Dict:
        """
        Fetch demographics from Census Bureau API (Free Tier - No API Key Required)

        API: https://api.census.gov/data/2023/acs/acs5

        Variables:
        - B01001_001E: Total population
        - B01002_001E: Median age
        - B19013_001E: Median household income
        - B15003_*: Educational attainment
        - B03002_*: Race and ethnicity
        """
        logger.info(f"Fetching demographics from Census Bureau for property {property.property_code}")

        try:
            # Determine ZIP code (if available)
            zip_code = property.zip_code if hasattr(property, 'zip_code') and property.zip_code else None

            if not zip_code:
                logger.warning(f"No ZIP code available for property {property.property_code}")
                return None  # Return None instead of mock data

            # Census API request - Free tier, no API key required
            # Use latest available ACS 5-year data (2023)
            url = "https://api.census.gov/data/2023/acs/acs5"
            params = {
                "get": "B01001_001E,B01002_001E,B19013_001E",  # Population, age, income
                "for": f"zip code tabulation area:{zip_code}"
            }
            
            # Add API key if available (for higher rate limits), but not required
            if hasattr(settings, 'CENSUS_API_KEY') and settings.CENSUS_API_KEY:
                params["key"] = settings.CENSUS_API_KEY

            response = await self.client.get(url, params=params, timeout=30.0)
            response.raise_for_status()

            data = response.json()

            # Parse response - First row is headers, second row is data
            if len(data) > 1:
                row = data[1]  # First data row after header
                
                # Parse values (Census uses -666666666 for null/missing data)
                population = None
                median_age = None
                median_income = None
                
                try:
                    if row[0] and row[0] != '-666666666' and row[0] != 'null':
                        population = int(row[0])
                except (ValueError, IndexError):
                    pass
                
                try:
                    if len(row) > 1 and row[1] and row[1] != '-666666666' and row[1] != 'null':
                        median_age = float(row[1])
                except (ValueError, IndexError):
                    pass
                
                try:
                    if len(row) > 2 and row[2] and row[2] != '-666666666' and row[2] != 'null':
                        median_income = int(row[2])
                except (ValueError, IndexError):
                    pass

                # Fetch education and ethnicity data
                education_data = await self._get_education_data(zip_code)
                ethnicity_data = await self._get_ethnicity_data(zip_code)
                
                # Estimate employment type from education data
                employment_type = self._estimate_employment_type(education_data)
                
                demographics = {
                    "population": population,
                    "median_age": median_age,
                    "median_income": median_income,
                    "education_level": education_data,
                    "ethnicity": ethnicity_data,
                    "employment_type": employment_type,
                    "data_source": "Census Bureau ACS 2023 5-Year",
                    "zip_code": zip_code,
                    "research_date": datetime.now().date().isoformat()
                }
                
                logger.info(f"Successfully fetched demographics for ZIP {zip_code}: Population={population}, Income=${median_income}")
                return demographics
            else:
                logger.warning(f"No data returned from Census API for ZIP {zip_code}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"Census API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error("Census API request timed out")
            return None
        except Exception as e:
            logger.error(f"Census API error: {str(e)}")
            return None

    async def _get_employment_data(self, property: Property) -> Dict:
        """
        Fetch employment data from Bureau of Labor Statistics API

        API: https://api.bls.gov/publicAPI/v2/timeseries/data/

        Series:
        - LAUCN{fips}03: Unemployment rate by county
        - CES0000000001: Total nonfarm employment
        """
        logger.info("Fetching employment data from BLS")

        if not hasattr(settings, 'BLS_API_KEY') or not settings.BLS_API_KEY:
            logger.warning("BLS API key not configured")
            return self._get_mock_employment()

        try:
            # Mock implementation for now
            return self._get_mock_employment()

        except Exception as e:
            logger.error(f"BLS API error: {str(e)}")
            return self._get_mock_employment()

    async def _get_nearby_developments(self, property: Property) -> List[Dict]:
        """
        Find nearby developments and construction projects

        Sources:
        - Building permit databases
        - Real estate news
        - Public records
        """
        logger.info("Searching for nearby developments")

        # Mock implementation
        return [
            {
                "name": "Downtown Revitalization Project",
                "type": "mixed_use",
                "status": "in_progress",
                "completion_date": "2026-Q3",
                "distance_miles": 1.2,
                "impact_score": 8.5,
                "description": "Major mixed-use development with retail and residential"
            }
        ]

    async def _get_market_analysis(self, property: Property) -> Dict:
        """
        Analyze local market using Google Places API

        Finds:
        - Nearby businesses
        - Competitor properties
        - Amenities
        """
        logger.info("Analyzing local market")

        if not hasattr(settings, 'GOOGLE_PLACES_API_KEY') or not settings.GOOGLE_PLACES_API_KEY:
            logger.warning("Google Places API key not configured")
            return self._get_mock_market_analysis()

        try:
            # Mock implementation
            return self._get_mock_market_analysis()

        except Exception as e:
            logger.error(f"Google Places API error: {str(e)}")
            return self._get_mock_market_analysis()

    def _get_sources(self) -> List[Dict]:
        """List all data sources used"""
        return [
            {
                "name": "U.S. Census Bureau",
                "type": "demographics",
                "url": "https://api.census.gov",
                "reliability": "high"
            },
            {
                "name": "Bureau of Labor Statistics",
                "type": "employment",
                "url": "https://api.bls.gov",
                "reliability": "high"
            },
            {
                "name": "Google Places",
                "type": "market_analysis",
                "url": "https://maps.googleapis.com",
                "reliability": "medium"
            }
        ]

    def _calculate_confidence(self, research_data: Dict) -> float:
        """
        Calculate confidence score based on data availability

        Factors:
        - Demographics available: 30%
        - Employment data available: 25%
        - Developments found: 20%
        - Market analysis complete: 25%
        """
        score = 0.0

        if research_data.get('demographics'):
            if research_data['demographics'].get('population'):
                score += 0.30

        if research_data.get('employment'):
            if research_data['employment'].get('unemployment_rate') is not None:
                score += 0.25

        if research_data.get('developments'):
            score += 0.20

        if research_data.get('market_analysis'):
            score += 0.25

        return round(score, 4)

    def _store_research(self, research_data: Dict):
        """Store research data in database"""
        try:
            # This would create a PropertyResearch model instance
            # For now, log only
            logger.info(f"Storing research data for property {research_data['property_id']}")
        except Exception as e:
            logger.error(f"Failed to store research: {str(e)}")

    # Mock data methods for when APIs are not configured

    def _get_mock_demographics(self) -> Dict:
        """Mock demographics data"""
        return {
            "population": 125000,
            "median_age": 38.5,
            "median_income": 72000,
            "education_level": {
                "high_school": 0.89,
                "bachelors": 0.42,
                "graduate": 0.18
            },
            "ethnicity": {
                "white": 0.62,
                "hispanic": 0.22,
                "black": 0.08,
                "asian": 0.06,
                "other": 0.02
            },
            "data_source": "Mock Data",
            "note": "Configure CENSUS_API_KEY for real data"
        }

    def _get_mock_employment(self) -> Dict:
        """Mock employment data"""
        return {
            "unemployment_rate": 0.034,
            "trend": "decreasing",
            "major_employers": [
                {"name": "Tech Corp", "employees": 5000},
                {"name": "Hospital System", "employees": 3200}
            ],
            "industries": {
                "technology": 0.28,
                "healthcare": 0.22,
                "retail": 0.15,
                "services": 0.35
            },
            "data_source": "Mock Data",
            "note": "Configure BLS_API_KEY for real data"
        }

    def _get_mock_market_analysis(self) -> Dict:
        """Mock market analysis"""
        return {
            "rental_rate_trend": "increasing",
            "occupancy_trend": "stable",
            "avg_rental_rate_psf": 28.50,
            "vacancy_rate": 0.06,
            "nearby_businesses_count": 145,
            "competitor_properties": 3,
            "data_source": "Mock Data",
            "note": "Configure GOOGLE_PLACES_API_KEY for real data"
        }

    async def _get_education_data(self, zip_code: str) -> Dict:
        """
        Fetch education data from Census Bureau API
        
        Variables:
        - B15003_022E: Bachelor's degree
        - B15003_023E: Master's degree
        - B15003_024E: Professional degree
        - B15003_025E: Doctorate degree
        - B15003_001E: Total population 25 years and over (denominator)
        """
        try:
            url = "https://api.census.gov/data/2023/acs/acs5"
            params = {
                "get": "B15003_001E,B15003_022E,B15003_023E,B15003_024E,B15003_025E",  # Total, Bachelor's, Master's, Professional, Doctorate
                "for": f"zip code tabulation area:{zip_code}"
            }
            
            if hasattr(settings, 'CENSUS_API_KEY') and settings.CENSUS_API_KEY:
                params["key"] = settings.CENSUS_API_KEY

            response = await self.client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if len(data) > 1:
                row = data[1]
                try:
                    total_25_plus = int(row[0]) if row[0] and row[0] != '-666666666' else 0
                    bachelors = int(row[1]) if len(row) > 1 and row[1] and row[1] != '-666666666' else 0
                    masters = int(row[2]) if len(row) > 2 and row[2] and row[2] != '-666666666' else 0
                    professional = int(row[3]) if len(row) > 3 and row[3] and row[3] != '-666666666' else 0
                    doctorate = int(row[4]) if len(row) > 4 and row[4] and row[4] != '-666666666' else 0
                    
                    # Calculate percentages
                    if total_25_plus > 0:
                        bachelors_pct = (bachelors / total_25_plus)
                        graduate_pct = ((masters + professional + doctorate) / total_25_plus)
                        # High school completion rate (approximate - would need more variables for exact)
                        high_school_pct = 1.0 - bachelors_pct  # Simplified estimate
                        
                        return {
                            "high_school": round(high_school_pct, 4),
                            "bachelors": round(bachelors_pct, 4),
                            "graduate": round(graduate_pct, 4)
                        }
                except (ValueError, IndexError, ZeroDivisionError) as e:
                    logger.warning(f"Error parsing education data: {e}")
            
            # Fallback to None if data unavailable
            return {
                "high_school": None,
                "bachelors": None,
                "graduate": None
            }
        except Exception as e:
            logger.error(f"Error fetching education data: {str(e)}")
            return {
                "high_school": None,
                "bachelors": None,
                "graduate": None
            }

    async def _get_ethnicity_data(self, zip_code: str) -> Dict:
        """
        Fetch ethnicity/race data from Census Bureau API
        
        Variables:
        - B03002_001E: Total population
        - B03002_003E: White alone
        - B03002_004E: Black or African American alone
        - B03002_005E: American Indian and Alaska Native alone
        - B03002_006E: Asian alone
        - B03002_012E: Hispanic or Latino
        """
        try:
            url = "https://api.census.gov/data/2023/acs/acs5"
            params = {
                "get": "B03002_001E,B03002_003E,B03002_004E,B03002_005E,B03002_006E,B03002_012E",
                "for": f"zip code tabulation area:{zip_code}"
            }
            
            if hasattr(settings, 'CENSUS_API_KEY') and settings.CENSUS_API_KEY:
                params["key"] = settings.CENSUS_API_KEY

            response = await self.client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if len(data) > 1:
                row = data[1]
                try:
                    total = int(row[0]) if row[0] and row[0] != '-666666666' else 0
                    white = int(row[1]) if len(row) > 1 and row[1] and row[1] != '-666666666' else 0
                    black = int(row[2]) if len(row) > 2 and row[2] and row[2] != '-666666666' else 0
                    native = int(row[3]) if len(row) > 3 and row[3] and row[3] != '-666666666' else 0
                    asian = int(row[4]) if len(row) > 4 and row[4] and row[4] != '-666666666' else 0
                    hispanic = int(row[5]) if len(row) > 5 and row[5] and row[5] != '-666666666' else 0
                    
                    # Calculate percentages
                    if total > 0:
                        return {
                            "white": round(white / total, 4),
                            "black": round(black / total, 4),
                            "native": round(native / total, 4),
                            "asian": round(asian / total, 4),
                            "hispanic": round(hispanic / total, 4),
                            "other": round(max(0, 1.0 - (white + black + native + asian + hispanic) / total), 4)
                        }
                except (ValueError, IndexError, ZeroDivisionError) as e:
                    logger.warning(f"Error parsing ethnicity data: {e}")
            
            # Fallback to None if data unavailable
            return {
                "white": None,
                "black": None,
                "native": None,
                "asian": None,
                "hispanic": None,
                "other": None
            }
        except Exception as e:
            logger.error(f"Error fetching ethnicity data: {str(e)}")
            return {
                "white": None,
                "black": None,
                "native": None,
                "asian": None,
                "hispanic": None,
                "other": None
            }
    
    def _estimate_employment_type(self, education_data: Dict) -> str:
        """
        Estimate employment type based on education levels
        Higher education = more professional employment
        """
        if not education_data or education_data.get("bachelors") is None:
            return "Data not available"
        
        bachelors_pct = education_data.get("bachelors", 0) or 0
        graduate_pct = education_data.get("graduate", 0) or 0
        
        professional_pct = bachelors_pct + graduate_pct
        
        if professional_pct >= 0.5:
            return f"{int(professional_pct * 100)}% Professional"
        elif professional_pct >= 0.3:
            return f"{int(professional_pct * 100)}% Professional"
        else:
            return f"{int(professional_pct * 100)}% Professional"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
