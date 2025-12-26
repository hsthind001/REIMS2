"""
Market Data Service

Centralized service for external data provider integration with caching,
source/vintage tagging, and audit trail tracking.

Supports:
- Census API (demographics)
- FRED API (economic indicators)
- BLS API (employment data)
- HUD API (housing data)
- OpenStreetMap (geocoding)
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from functools import wraps
import hashlib
import json
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# In-memory cache with TTL (will upgrade to Redis in production)
_market_data_cache: Dict[str, Dict[str, Any]] = {}


def cache_with_ttl(ttl_seconds: int = 3600):
    """
    Decorator for caching API responses with TTL.

    Args:
        ttl_seconds: Time to live in seconds (default 1 hour)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = hashlib.md5(
                f"{func.__name__}_{str(args)}_{str(kwargs)}".encode()
            ).hexdigest()

            # Check cache
            if cache_key in _market_data_cache:
                cached = _market_data_cache[cache_key]
                age = time.time() - cached['timestamp']
                if age < ttl_seconds:
                    logger.info(f"Cache HIT for {func.__name__} (age: {age:.1f}s)")
                    return cached['data']
                else:
                    logger.info(f"Cache EXPIRED for {func.__name__} (age: {age:.1f}s)")

            # Cache miss - fetch data
            logger.info(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)

            # Store in cache
            _market_data_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }

            return result
        return wrapper
    return decorator


class MarketDataService:
    """
    Centralized service for external market data integration.

    Features:
    - Automatic caching with TTL
    - Source and vintage tagging
    - Data quality validation
    - Rate limiting and retry logic
    - Audit trail logging
    """

    # API Base URLs
    CENSUS_API_BASE = "https://api.census.gov/data"
    FRED_API_BASE = "https://api.stlouisfed.org/fred"
    BLS_API_BASE = "https://api.bls.gov/publicAPI/v2"
    HUD_API_BASE = "https://www.huduser.gov/hudapi/public"
    NOMINATIM_API_BASE = "https://nominatim.openstreetmap.org"

    # Rate limiting (requests per minute)
    RATE_LIMITS = {
        'census': 50,
        'fred': 120,
        'bls': 25,
        'hud': 60,
        'nominatim': 1  # Very conservative for OSM
    }

    # Request tracking for rate limiting
    _request_history: Dict[str, List[float]] = {}

    def __init__(self, db: Session, census_api_key: Optional[str] = None, fred_api_key: Optional[str] = None):
        """
        Initialize Market Data Service.

        Args:
            db: Database session
            census_api_key: Census API key (optional but recommended)
            fred_api_key: FRED API key (required for FRED data)
        """
        self.db = db
        self.census_api_key = census_api_key
        self.fred_api_key = fred_api_key

    def _check_rate_limit(self, source: str) -> bool:
        """
        Check if we can make a request without exceeding rate limit.

        Args:
            source: Data source name ('census', 'fred', 'bls', 'hud', 'nominatim')

        Returns:
            True if request is allowed, False if rate limit would be exceeded
        """
        if source not in self._request_history:
            self._request_history[source] = []

        # Clean up old requests (older than 1 minute)
        current_time = time.time()
        self._request_history[source] = [
            t for t in self._request_history[source]
            if current_time - t < 60
        ]

        # Check if we're under the limit
        limit = self.RATE_LIMITS.get(source, 60)
        if len(self._request_history[source]) >= limit:
            logger.warning(f"Rate limit reached for {source} ({limit} requests/min)")
            return False

        return True

    def _record_request(self, source: str):
        """Record a request for rate limiting."""
        if source not in self._request_history:
            self._request_history[source] = []
        self._request_history[source].append(time.time())

    def _wait_for_rate_limit(self, source: str):
        """Wait if necessary to avoid rate limiting."""
        while not self._check_rate_limit(source):
            logger.info(f"Waiting for rate limit window for {source}...")
            time.sleep(1)

    def fetch_with_retry(
        self,
        source: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data from external API with retry logic and rate limiting.

        Args:
            source: Data source name
            url: API endpoint URL
            params: Query parameters
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            API response as dict, or None on failure
        """
        self._wait_for_rate_limit(source)

        for attempt in range(max_retries):
            try:
                self._record_request(source)

                logger.info(f"Fetching from {source}: {url} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching from {source} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error fetching from {source}: {e}")
                if e.response.status_code == 429:  # Rate limit
                    logger.warning(f"Rate limited by {source}, waiting 60 seconds...")
                    time.sleep(60)
                elif e.response.status_code >= 500:  # Server error
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                else:
                    break  # Don't retry client errors

            except Exception as e:
                logger.error(f"Error fetching from {source}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def tag_data_source(
        self,
        data: Dict[str, Any],
        source: str,
        vintage: Optional[str] = None,
        confidence: float = 100.0,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tag data with source, vintage, confidence, and metadata.

        Args:
            data: Raw data from API
            source: Data source name
            vintage: Data vintage/year (e.g., "2023", "2024-Q1")
            confidence: Confidence score (0-100)
            extra_metadata: Additional metadata

        Returns:
            Tagged data with lineage information
        """
        return {
            'data': data,
            'lineage': {
                'source': source,
                'vintage': vintage or datetime.now().strftime('%Y'),
                'confidence': confidence,
                'fetched_at': datetime.now().isoformat(),
                'extra_metadata': extra_metadata or {}
            }
        }

    def validate_data(
        self,
        data: Any,
        required_fields: Optional[List[str]] = None,
        expected_type: Optional[type] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate data quality.

        Args:
            data: Data to validate
            required_fields: Required field names (for dict data)
            expected_type: Expected data type

        Returns:
            (is_valid, error_message)
        """
        # Type validation
        if expected_type and not isinstance(data, expected_type):
            return False, f"Expected {expected_type}, got {type(data)}"

        # Required fields validation
        if required_fields and isinstance(data, dict):
            missing = [f for f in required_fields if f not in data]
            if missing:
                return False, f"Missing required fields: {', '.join(missing)}"

        # Check for None/empty
        if data is None:
            return False, "Data is None"
        if isinstance(data, (list, dict)) and len(data) == 0:
            return False, "Data is empty"

        return True, None

    def log_data_pull(
        self,
        source: str,
        endpoint: str,
        status: str,
        records_fetched: int = 0,
        error_message: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log data pull to audit trail.

        Args:
            source: Data source name
            endpoint: API endpoint
            status: 'success' or 'failure'
            records_fetched: Number of records fetched
            error_message: Error message if failed
            extra_metadata: Additional metadata
        """
        from app.models.audit_trail import AuditTrail

        try:
            audit = AuditTrail(
                action=f"market_data_pull_{source}",
                entity_type="market_data",
                entity_id=None,
                details={
                    'source': source,
                    'endpoint': endpoint,
                    'status': status,
                    'records_fetched': records_fetched,
                    'error_message': error_message,
                    'timestamp': datetime.now().isoformat(),
                    'extra_metadata': extra_metadata or {}
                }
            )
            self.db.add(audit)
            self.db.commit()
            logger.info(f"Logged data pull: {source} - {status}")
        except Exception as e:
            logger.error(f"Failed to log data pull: {e}")
            self.db.rollback()

    # ========== Census API ==========

    @cache_with_ttl(ttl_seconds=86400)  # 24 hours
    def fetch_census_demographics(
        self,
        latitude: float,
        longitude: float,
        year: int = 2021
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demographics from Census API for a location.

        Args:
            latitude: Property latitude
            longitude: Property longitude
            year: Census year (default: 2021 - latest ACS 5-year)

        Returns:
            Tagged demographics data or None
        """
        try:
            # First, get census tract from coordinates
            geocode_url = f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
            geocode_params = {
                'x': longitude,
                'y': latitude,
                'benchmark': 'Public_AR_Current',
                'vintage': 'Current_Current',
                'format': 'json'
            }

            geocode_result = self.fetch_with_retry('census', geocode_url, geocode_params)
            if not geocode_result or 'result' not in geocode_result:
                logger.error("Failed to geocode location")
                self.log_data_pull('census', 'geocode', 'failure', error_message="Geocoding failed")
                return None

            # Extract tract, county, state
            geographies = geocode_result['result']['geographies']
            if 'Census Tracts' not in geographies or len(geographies['Census Tracts']) == 0:
                logger.error("No census tract found")
                return None

            tract_info = geographies['Census Tracts'][0]
            state_fips = tract_info['STATE']
            county_fips = tract_info['COUNTY']
            tract_code = tract_info['TRACT']

            # Fetch ACS 5-year data
            acs_url = f"{self.CENSUS_API_BASE}/{year}/acs/acs5"

            # Demographics variables
            variables = [
                'B01003_001E',  # Total population
                'B19013_001E',  # Median household income
                'B25077_001E',  # Median home value
                'B25064_001E',  # Median gross rent
                'B23025_005E',  # Unemployment count
                'B23025_003E',  # In labor force count
                'B01002_001E',  # Median age
                'B15003_022E',  # Bachelor's degree
                'B15003_023E',  # Master's degree
                'B15003_024E',  # Professional degree
                'B15003_025E',  # Doctorate degree
                'B15003_001E',  # Total education population
                'B25024_002E',  # Single-family units
                'B25024_003E',  # Multi-family 2-4 units
                'B25024_004E',  # Multi-family 5-9 units
                'B25024_005E',  # Multi-family 10-19 units
                'B25024_006E',  # Multi-family 20-49 units
                'B25024_007E',  # Multi-family 50+ units
            ]

            params = {
                'get': ','.join(variables),
                'for': f'tract:{tract_code}',
                'in': f'state:{state_fips} county:{county_fips}'
            }

            if self.census_api_key:
                params['key'] = self.census_api_key

            acs_result = self.fetch_with_retry('census', acs_url, params)

            if not acs_result or len(acs_result) < 2:
                logger.error("Failed to fetch ACS data")
                self.log_data_pull('census', 'acs5', 'failure', error_message="No ACS data returned")
                return None

            # Parse results (first row is headers, second is data)
            headers = acs_result[0]
            data = acs_result[1]
            acs_data = dict(zip(headers, data))

            # Calculate derived metrics
            total_pop = int(acs_data.get('B01003_001E', 0))
            labor_force = int(acs_data.get('B23025_003E', 0))
            unemployed = int(acs_data.get('B23025_005E', 0))
            education_total = int(acs_data.get('B15003_001E', 1))
            bachelors = int(acs_data.get('B15003_022E', 0))
            masters = int(acs_data.get('B15003_023E', 0))
            professional = int(acs_data.get('B15003_024E', 0))
            doctorate = int(acs_data.get('B15003_025E', 0))

            unemployment_rate = (unemployed / labor_force * 100) if labor_force > 0 else 0
            college_educated_pct = ((bachelors + masters + professional + doctorate) / education_total * 100) if education_total > 0 else 0

            demographics = {
                'population': total_pop,
                'median_household_income': int(acs_data.get('B19013_001E', 0)),
                'median_home_value': int(acs_data.get('B25077_001E', 0)),
                'median_gross_rent': int(acs_data.get('B25064_001E', 0)),
                'unemployment_rate': round(unemployment_rate, 2),
                'median_age': float(acs_data.get('B01002_001E', 0)),
                'college_educated_pct': round(college_educated_pct, 2),
                'housing_units': {
                    'single_family': int(acs_data.get('B25024_002E', 0)),
                    'multifamily_2_4': int(acs_data.get('B25024_003E', 0)),
                    'multifamily_5_9': int(acs_data.get('B25024_004E', 0)),
                    'multifamily_10_19': int(acs_data.get('B25024_005E', 0)),
                    'multifamily_20_49': int(acs_data.get('B25024_006E', 0)),
                    'multifamily_50_plus': int(acs_data.get('B25024_007E', 0))
                },
                'geography': {
                    'state_fips': state_fips,
                    'county_fips': county_fips,
                    'tract': tract_code
                }
            }

            self.log_data_pull('census', 'acs5', 'success', records_fetched=1)

            return self.tag_data_source(
                demographics,
                source='census_acs5',
                vintage=str(year),
                confidence=95.0,
                extra_metadata={'tract': tract_code, 'state': state_fips, 'county': county_fips}
            )

        except Exception as e:
            logger.error(f"Error fetching census demographics: {e}")
            self.log_data_pull('census', 'acs5', 'failure', error_message=str(e))
            return None

    # ========== FRED API ==========

    @cache_with_ttl(ttl_seconds=86400)  # 24 hours
    def fetch_fred_economic_indicators(
        self,
        msa_code: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch economic indicators from FRED API.

        Args:
            msa_code: MSA code (e.g., "41860" for San Francisco)

        Returns:
            Tagged economic indicators or None
        """
        if not self.fred_api_key:
            logger.error("FRED API key required")
            return None

        try:
            indicators = {}

            # National indicators
            national_series = {
                'gdp_growth': 'A191RL1Q225SBEA',  # Real GDP growth rate
                'unemployment_rate': 'UNRATE',  # National unemployment
                'inflation_rate': 'CPIAUCSL',  # CPI
                'fed_funds_rate': 'FEDFUNDS',  # Federal funds rate
                'mortgage_rate_30y': 'MORTGAGE30US',  # 30-year mortgage rate
                'recession_probability': 'RECPROUSM156N'  # Recession probability
            }

            for indicator, series_id in national_series.items():
                url = f"{self.FRED_API_BASE}/series/observations"
                params = {
                    'series_id': series_id,
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 1  # Latest value
                }

                result = self.fetch_with_retry('fred', url, params)
                if result and 'observations' in result and len(result['observations']) > 0:
                    latest = result['observations'][0]
                    indicators[indicator] = {
                        'value': float(latest['value']) if latest['value'] != '.' else None,
                        'date': latest['date']
                    }

            # MSA-specific indicators if MSA code provided
            if msa_code:
                msa_series = {
                    'msa_unemployment': f'UR{msa_code}',  # MSA unemployment
                    'msa_gdp': f'NGMP{msa_code}',  # MSA GDP
                }

                for indicator, series_id in msa_series.items():
                    url = f"{self.FRED_API_BASE}/series/observations"
                    params = {
                        'series_id': series_id,
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': 1
                    }

                    result = self.fetch_with_retry('fred', url, params)
                    if result and 'observations' in result and len(result['observations']) > 0:
                        latest = result['observations'][0]
                        indicators[indicator] = {
                            'value': float(latest['value']) if latest['value'] != '.' else None,
                            'date': latest['date']
                        }

            self.log_data_pull('fred', 'series/observations', 'success', records_fetched=len(indicators))

            return self.tag_data_source(
                indicators,
                source='fred',
                vintage=datetime.now().strftime('%Y-%m'),
                confidence=98.0,
                extra_metadata={'msa_code': msa_code}
            )

        except Exception as e:
            logger.error(f"Error fetching FRED data: {e}")
            self.log_data_pull('fred', 'series/observations', 'failure', error_message=str(e))
            return None

    # ========== OpenStreetMap Geocoding ==========

    @cache_with_ttl(ttl_seconds=2592000)  # 30 days (addresses don't change often)
    def geocode_address(
        self,
        address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Geocode an address using OpenStreetMap Nominatim.

        Args:
            address: Full address string

        Returns:
            Tagged geocoding result with lat/lon
        """
        try:
            url = f"{self.NOMINATIM_API_BASE}/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'REIMS2-Market-Intelligence/1.0'
            }

            # Special handling for Nominatim (requires User-Agent)
            self._wait_for_rate_limit('nominatim')
            self._record_request('nominatim')

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            if not result or len(result) == 0:
                logger.warning(f"No geocoding result for: {address}")
                self.log_data_pull('nominatim', 'search', 'failure', error_message="No results")
                return None

            location = result[0]
            geocoded = {
                'latitude': float(location['lat']),
                'longitude': float(location['lon']),
                'formatted_address': location.get('display_name'),
                'address_details': location.get('address', {}),
                'importance': float(location.get('importance', 0))
            }

            self.log_data_pull('nominatim', 'search', 'success', records_fetched=1)

            return self.tag_data_source(
                geocoded,
                source='nominatim',
                confidence=85.0,
                extra_metadata={'original_address': address}
            )

        except Exception as e:
            logger.error(f"Error geocoding address: {e}")
            self.log_data_pull('nominatim', 'search', 'failure', error_message=str(e))
            return None

    # ========== LOCATION INTELLIGENCE (PHASE 2) ==========

    @cache_with_ttl(ttl_seconds=604800)  # 7 days
    def fetch_location_intelligence(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive location intelligence data.

        Includes:
        - Walk/Transit/Bike scores (calculated)
        - Amenity counts within radius
        - Crime index (placeholder - would integrate with local APIs)
        - School ratings (placeholder - would integrate with GreatSchools API)

        Args:
            latitude: Property latitude
            longitude: Property longitude

        Returns:
            Tagged location intelligence data with lineage
        """
        try:
            logger.info(f"Fetching location intelligence for ({latitude}, {longitude})")

            # Fetch amenity counts from OpenStreetMap
            amenities = self._fetch_amenities_osm(latitude, longitude)

            # Calculate transit access
            transit = self._calculate_transit_access(latitude, longitude)

            # Calculate walkability/bikeability scores
            walk_score = self._calculate_walk_score(amenities)
            transit_score = self._calculate_transit_score(transit)
            bike_score = self._calculate_bike_score(amenities)

            # Placeholder for crime data (would integrate with local crime APIs)
            crime_index = 50.0  # 0-100 scale, 50 = average

            # Placeholder for school ratings (would integrate with GreatSchools API)
            school_rating_avg = 7.0  # 0-10 scale

            location_intel = {
                'walk_score': walk_score,
                'transit_score': transit_score,
                'bike_score': bike_score,
                'amenities': amenities,
                'transit_access': transit,
                'crime_index': crime_index,
                'school_rating_avg': school_rating_avg
            }

            self.log_data_pull('osm_overpass', 'location_intelligence', 'success', records_fetched=1)

            return self.tag_data_source(
                location_intel,
                source='osm_overpass',
                confidence=75.0,
                extra_metadata={'latitude': latitude, 'longitude': longitude}
            )

        except Exception as e:
            logger.error(f"Error fetching location intelligence: {e}")
            self.log_data_pull('osm_overpass', 'location_intelligence', 'failure', error_message=str(e))
            return None

    def _fetch_amenities_osm(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, int]:
        """
        Fetch amenity counts from OpenStreetMap Overpass API.

        Args:
            latitude: Center latitude
            longitude: Center longitude

        Returns:
            Dictionary of amenity counts
        """
        try:
            # Overpass API endpoint
            overpass_url = "https://overpass-api.de/api/interpreter"

            # Search radii in meters
            radius_1mi = 1609  # 1 mile
            radius_2mi = 3218  # 2 miles
            radius_5mi = 8047  # 5 miles

            # Build Overpass QL query
            query = f"""
            [out:json][timeout:25];
            (
              node["shop"="supermarket"](around:{radius_1mi},{latitude},{longitude});
              node["amenity"="restaurant"](around:{radius_1mi},{latitude},{longitude});
              node["amenity"="school"](around:{radius_2mi},{latitude},{longitude});
              node["amenity"="hospital"](around:{radius_5mi},{latitude},{longitude});
              node["leisure"="park"](around:{radius_1mi},{latitude},{longitude});
              node["amenity"="bus_station"](around:805,{latitude},{longitude});
              node["railway"="station"](around:{radius_1mi},{latitude},{longitude});
            );
            out count;
            """

            self._wait_for_rate_limit('nominatim')  # Reuse Nominatim rate limit
            self._record_request('nominatim')

            response = httpx.post(
                overpass_url,
                data={'data': query},
                timeout=30.0
            )
            response.raise_for_status()

            data = response.json()

            # Parse counts from Overpass response
            # Note: This is simplified - real implementation would parse element counts
            amenities = {
                'grocery_stores_1mi': len([e for e in data.get('elements', []) if e.get('tags', {}).get('shop') == 'supermarket']),
                'restaurants_1mi': len([e for e in data.get('elements', []) if e.get('tags', {}).get('amenity') == 'restaurant']),
                'schools_2mi': len([e for e in data.get('elements', []) if e.get('tags', {}).get('amenity') == 'school']),
                'hospitals_5mi': len([e for e in data.get('elements', []) if e.get('tags', {}).get('amenity') == 'hospital']),
                'parks_1mi': len([e for e in data.get('elements', []) if e.get('tags', {}).get('leisure') == 'park']),
            }

            logger.info(f"Found amenities: {amenities}")
            return amenities

        except Exception as e:
            logger.warning(f"Error fetching amenities from OSM: {e}")
            # Return default values if API fails
            return {
                'grocery_stores_1mi': 0,
                'restaurants_1mi': 0,
                'schools_2mi': 0,
                'hospitals_5mi': 0,
                'parks_1mi': 0
            }

    def _calculate_transit_access(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Calculate transit access metrics.

        Args:
            latitude: Property latitude
            longitude: Property longitude

        Returns:
            Transit access metrics
        """
        try:
            # Query OSM for transit stops nearby
            overpass_url = "https://overpass-api.de/api/interpreter"

            query = f"""
            [out:json][timeout:15];
            (
              node["highway"="bus_stop"](around:805,{latitude},{longitude});
              node["railway"="station"](around:1609,{latitude},{longitude});
              node["railway"="subway_entrance"](around:1609,{latitude},{longitude});
            );
            out count;
            """

            self._wait_for_rate_limit('nominatim')
            self._record_request('nominatim')

            response = httpx.post(
                overpass_url,
                data={'data': query},
                timeout=20.0
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get('elements', [])

            transit = {
                'bus_stops_0_5mi': len([e for e in elements if e.get('tags', {}).get('highway') == 'bus_stop']),
                'subway_stations_1mi': len([e for e in elements if e.get('tags', {}).get('railway') in ['station', 'subway_entrance']]),
                'commute_time_downtown_min': 30  # Placeholder - would calculate actual distance/time
            }

            return transit

        except Exception as e:
            logger.warning(f"Error calculating transit access: {e}")
            return {
                'bus_stops_0_5mi': 0,
                'subway_stations_1mi': 0,
                'commute_time_downtown_min': 60
            }

    def _calculate_walk_score(self, amenities: Dict[str, int]) -> int:
        """
        Calculate walkability score (0-100) based on amenities.

        Simplified algorithm:
        - More nearby amenities = higher score
        - Grocery stores are weighted heavily
        - Restaurants indicate walkable neighborhood
        - Parks add to walkability

        Args:
            amenities: Dictionary of amenity counts

        Returns:
            Walk score (0-100)
        """
        score = 0

        # Grocery stores (max 30 points)
        grocery = min(amenities.get('grocery_stores_1mi', 0) * 10, 30)
        score += grocery

        # Restaurants (max 25 points)
        restaurants = min(amenities.get('restaurants_1mi', 0) * 2, 25)
        score += restaurants

        # Schools (max 15 points)
        schools = min(amenities.get('schools_2mi', 0) * 5, 15)
        score += schools

        # Parks (max 15 points)
        parks = min(amenities.get('parks_1mi', 0) * 7, 15)
        score += parks

        # Hospitals (max 15 points)
        hospitals = min(amenities.get('hospitals_5mi', 0) * 5, 15)
        score += hospitals

        return min(int(score), 100)

    def _calculate_transit_score(self, transit: Dict[str, Any]) -> int:
        """
        Calculate transit score (0-100) based on public transportation access.

        Args:
            transit: Transit access metrics

        Returns:
            Transit score (0-100)
        """
        score = 0

        # Bus stops (max 40 points)
        bus_stops = min(transit.get('bus_stops_0_5mi', 0) * 8, 40)
        score += bus_stops

        # Subway stations (max 50 points)
        subway = min(transit.get('subway_stations_1mi', 0) * 25, 50)
        score += subway

        # Commute time (max 10 points)
        commute = transit.get('commute_time_downtown_min', 60)
        if commute <= 15:
            score += 10
        elif commute <= 30:
            score += 5

        return min(int(score), 100)

    def _calculate_bike_score(self, amenities: Dict[str, int]) -> int:
        """
        Calculate bike score (0-100) based on amenities and infrastructure.

        Note: Real implementation would check for bike lanes, trails, etc.
        This is simplified based on density of destinations.

        Args:
            amenities: Dictionary of amenity counts

        Returns:
            Bike score (0-100)
        """
        # Simplified: Bike score is typically lower than walk score
        # Real implementation would check for bike infrastructure
        walk_equivalent = self._calculate_walk_score(amenities)

        # Reduce by 20% as baseline (fewer places have good bike infrastructure)
        bike_score = int(walk_equivalent * 0.8)

        return min(bike_score, 100)
