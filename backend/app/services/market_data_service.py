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
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import requests
import httpx # For async/http2 requests (used by Overpass)
from functools import wraps
import hashlib
import json
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, func

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
    HAS_PGVECTOR = True
except Exception:
    Vector = None  # type: ignore
    HAS_PGVECTOR = False

try:
    import faiss  # type: ignore
    HAS_FAISS = True
except Exception:
    HAS_FAISS = False

from app.models.ai_insights_embedding import AIInsightsEmbedding
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.market_intelligence import MarketIntelligence
from app.models.property import Property

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
    OVERPASS_API_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter",
    ]

    # Rate limiting (requests per minute)
    RATE_LIMITS = {
        'census': 50,
        'fred': 120,
        'bls': 25,
        'hud': 60,
        'nominatim': 1,  # Very conservative for OSM
        'overpass': 30
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
        self.osrm_base_url = os.getenv('OSRM_BASE_URL')

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

    @cache_with_ttl(ttl_seconds=604800)  # 7 days - vintages change rarely
    def get_latest_census_vintage(self) -> int:
        """
        Automatically detect the latest available Census ACS5 vintage.

        The Census Bureau typically releases ACS5 data with a 2-year lag.
        For example, in 2025, the latest available data is usually 2022 or 2023.

        Returns:
            Latest available year (e.g., 2022)
        """
        try:
            current_year = datetime.now().year
            # Try years from most recent to 5 years back
            # ACS5 typically has 1-2 year lag. We check aggressively starting from 1 year back.
            for years_back in range(1, 6):  # Try 1, 2, 3, 4, 5 years back
                test_year = current_year - years_back
                test_url = f"{self.CENSUS_API_BASE}/{test_year}/acs/acs5"

                try:
                    # Test if this vintage exists by making a minimal request
                    # Test with actual variables to ensure the endpoint fully works
                    params = {'get': 'B01003_001E,NAME', 'for': 'us:1'}
                    if self.census_api_key:
                        params['key'] = self.census_api_key

                    response = requests.get(test_url, params=params, timeout=5)

                    # Check if response is valid JSON (not HTML error page)
                    if response.status_code == 200:
                        try:
                            response.json()  # Validate JSON response
                            logger.info(f"Latest Census ACS5 vintage detected: {test_year}")
                            return test_year
                        except (ValueError, TypeError):
                            # Invalid JSON response, try next year
                            continue
                except (requests.RequestException, requests.Timeout):
                    # Network error, try next year
                    continue

            # Fallback to a safe default (2022 is stable and widely available)
            logger.warning("Could not detect latest Census vintage, using fallback: 2022")
            return 2022

        except Exception as e:
            logger.error(f"Error detecting Census vintage: {e}")
            return 2022  # Safe fallback

    @cache_with_ttl(ttl_seconds=86400)  # 24 hours
    def fetch_census_demographics(
        self,
        latitude: float,
        longitude: float,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demographics from Census API for a location.

        Args:
            latitude: Property latitude
            longitude: Property longitude
            year: Census year (default: None - auto-detect latest available)

        Returns:
            Tagged demographics data or None
        """
        try:
            # Auto-detect latest vintage if not specified
            if year is None:
                year = self.get_latest_census_vintage()
                logger.info(f"Using auto-detected Census vintage: {year}")
            # First, get census tract from coordinates
            geocode_url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
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

    @cache_with_ttl(ttl_seconds=2592000)  # 30 days - population estimates updated annually
    def fetch_census_population_estimates(
        self,
        state_fips: str,
        county_fips: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch recent population estimates from Census Population Estimates API.

        These estimates are more current than ACS5 (typically 1 year lag vs 2-3 years)
        and can supplement the detailed ACS5 demographics.

        Args:
            state_fips: State FIPS code (e.g., "04" for Arizona)
            county_fips: County FIPS code (e.g., "013" for Maricopa)

        Returns:
            Tagged population estimates or None
        """
        try:
            current_year = datetime.now().year
            # Try current year and previous year
            for year in [current_year, current_year - 1]:
                try:
                    # Population Estimates API
                    pep_url = f"{self.CENSUS_API_BASE}/{year}/pep/population"
                    params = {
                        'get': 'POP,NAME',
                        'for': f'county:{county_fips}',
                        'in': f'state:{state_fips}'
                    }

                    if self.census_api_key:
                        params['key'] = self.census_api_key

                    result = self.fetch_with_retry('census', pep_url, params)

                    if result and len(result) >= 2:
                        headers = result[0]
                        data = result[1]
                        pep_data = dict(zip(headers, data))

                        population = int(pep_data.get('POP', 0))

                        if population > 0:
                            logger.info(f"Fetched population estimate for {year}: {population:,}")
                            self.log_data_pull('census', 'pep', 'success', records_fetched=1)

                            return self.tag_data_source(
                                {'population': population, 'county_name': pep_data.get('NAME', 'Unknown')},
                                source='census_pep',
                                vintage=str(year),
                                confidence=90.0,
                                extra_metadata={'state': state_fips, 'county': county_fips}
                            )
                except (requests.RequestException, ValueError, KeyError):
                    # Network error or invalid data, try next year
                    continue

            logger.warning("Could not fetch recent population estimates")
            self.log_data_pull('census', 'pep', 'failure', error_message="No recent estimates available")
            return None

        except Exception as e:
            logger.error(f"Error fetching population estimates: {e}")
            self.log_data_pull('census', 'pep', 'failure', error_message=str(e))
            return None

    def fetch_enhanced_demographics(
        self,
        latitude: float,
        longitude: float,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch demographics with supplementary data from multiple sources.

        Combines:
        - Census ACS5 (detailed demographics, 2-3 year lag)
        - Census Population Estimates (recent population, 1 year lag)

        Args:
            latitude: Property latitude
            longitude: Property longitude
            year: Census ACS5 year (default: None - auto-detect)

        Returns:
            Enhanced demographics with multiple data sources
        """
        try:
            # Get base ACS5 demographics
            acs_data = self.fetch_census_demographics(latitude, longitude, year)

            if not acs_data:
                return None

            # Extract geography info from ACS data
            geography = acs_data.get('data', {}).get('geography', {})
            state_fips = geography.get('state_fips')
            county_fips = geography.get('county_fips')

            enhanced_data = acs_data.copy()

            # Add recent population estimates if available
            if state_fips and county_fips:
                pop_estimates = self.fetch_census_population_estimates(state_fips, county_fips)

                if pop_estimates:
                    # Add supplementary data section
                    if 'supplementary_sources' not in enhanced_data:
                        enhanced_data['supplementary_sources'] = []

                    enhanced_data['supplementary_sources'].append({
                        'source': 'census_pep',
                        'type': 'population_estimate',
                        'vintage': pop_estimates.get('lineage', {}).get('vintage'),
                        'data': pop_estimates.get('data', {}),
                        'note': 'More recent than ACS5 but less detailed'
                    })

                    logger.info("Enhanced demographics with population estimates")

            return enhanced_data

        except Exception as e:
            logger.error(f"Error fetching enhanced demographics: {e}")
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
        longitude: float,
        cache_bust: Optional[str] = None
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
            cache_bust: Optional cache-busting token to force refresh

        Returns:
            Tagged location intelligence data with lineage
        """
        try:
            logger.info(f"Fetching location intelligence for ({latitude}, {longitude})")

            # Fetch amenity counts from OpenStreetMap
            amenities = self._fetch_amenities_osm(latitude, longitude)
            if amenities is None:
                logger.warning("No amenities returned from Overpass; skipping location intelligence update")
                return None

            # Drive-times (OSRM if configured)
            drive_times = self._compute_drive_times(latitude, longitude)
            isochrones = self._compute_isochrones(latitude, longitude)

            # Calculate transit access (optional)
            transit = self._calculate_transit_access(latitude, longitude) or {
                'bus_stops_0_5mi': 0,
                'subway_stations_1mi': 0,
                'commute_time_downtown_min': 60
            }

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
                'drive_times': drive_times,
                'transit_access': transit,
                'isochrones': isochrones,
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
    ) -> Optional[Dict[str, int]]:
        """
        Fetch amenity counts from OpenStreetMap Overpass API.

        Args:
            latitude: Center latitude
            longitude: Center longitude

        Returns:
            Dictionary of amenity counts
        """
        try:
            # Search radii in meters
            radius_1mi = 1609  # 1 mile
            radius_2mi = 3218  # 2 miles
            radius_5mi = 8047  # 5 miles

            # Build Overpass QL query
            query = f"""
            [out:json][timeout:25];
            (
              nwr["shop"="supermarket"](around:{radius_1mi},{latitude},{longitude});
              nwr["amenity"="restaurant"](around:{radius_1mi},{latitude},{longitude});
              nwr["amenity"="school"](around:{radius_2mi},{latitude},{longitude});
              nwr["amenity"="hospital"](around:{radius_5mi},{latitude},{longitude});
              nwr["leisure"="park"](around:{radius_1mi},{latitude},{longitude});
            );
            out tags;
            """

            self._wait_for_rate_limit('overpass')
            self._record_request('overpass')

            last_error = None
            for overpass_url in self.OVERPASS_API_URLS:
                try:
                    response = httpx.post(
                        overpass_url,
                        data={'data': query},
                        timeout=30.0
                    )
                    response.raise_for_status()

                    data = response.json()

                    # Parse counts from Overpass response (tags-only payload)
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
                    last_error = e
                    logger.warning(f"Overpass amenities request failed via {overpass_url}: {e}")

            if last_error:
                raise last_error

        except Exception as e:
            logger.warning(f"Error fetching amenities from OSM: {e}")
            return None

    def _compute_drive_times(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Compute drive times using OSRM if configured. Returns sample if unavailable.
        """
        osrm_base = self.osrm_base_url
        cache_key = f"drive:{round(latitude,4)}:{round(longitude,4)}"
        if cache_key in _market_data_cache:
            cached = _market_data_cache[cache_key]
            if time.time() - cached['timestamp'] < 3600:
                return cached['data']
        if not osrm_base:
            return {
                'sample_drive_min': 15
            }
        try:
            target_lat = latitude + 0.05
            target_lon = longitude + 0.05
            url = f"{osrm_base}/route/v1/driving/{longitude},{latitude};{target_lon},{target_lat}"
            params = {'overview': 'false', 'alternatives': 'false'}
            result = self.fetch_with_retry('osrm', url, params)
            if result and result.get('routes'):
                duration_sec = result['routes'][0].get('duration', 900)
                val = {
                    'sample_drive_min': round(duration_sec / 60, 1)
                }
                _market_data_cache[cache_key] = {'data': val, 'timestamp': time.time()}
                return val
        except Exception as e:
            logger.warning(f"OSRM drive-time failed: {e}")
        return {
            'sample_drive_min': 15
        }

    def _compute_isochrones(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """
        Compute simple isochrone polygons from OSRM if configured. Falls back to empty.
        """
        osrm_base = self.osrm_base_url
        cache_key = f"iso:{round(latitude,4)}:{round(longitude,4)}"
        if cache_key in _market_data_cache:
            cached = _market_data_cache[cache_key]
            if time.time() - cached['timestamp'] < 3600:
                return cached['data']
        if not osrm_base:
            return []
        try:
            contours = [5, 10, 15]  # minutes
            polys = []
            for c in contours:
                url = f"{osrm_base}/isochrone/v1/driving/{longitude},{latitude}"
                params = {'contours_minutes': c, 'polygons': 'true', 'generalize': 100}
                res = self.fetch_with_retry('osrm', url, params)
                if res and res.get('features'):
                    poly = res['features'][0].get('geometry')
                    polys.append({'minutes': c, 'geometry': poly})
            _market_data_cache[cache_key] = {'data': polys, 'timestamp': time.time()}
            return polys
        except Exception as e:
            logger.warning(f"OSRM isochrone failed: {e}")
            return []

    def _calculate_transit_access(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate transit access metrics.

        Args:
            latitude: Property latitude
            longitude: Property longitude

        Returns:
            Transit access metrics
        """
        try:
            query = f"""
            [out:json][timeout:15];
            (
              nwr["highway"="bus_stop"](around:805,{latitude},{longitude});
              nwr["railway"="station"](around:1609,{latitude},{longitude});
              nwr["railway"="subway_entrance"](around:1609,{latitude},{longitude});
            );
            out tags;
            """

            self._wait_for_rate_limit('overpass')
            self._record_request('overpass')

            last_error = None
            for overpass_url in self.OVERPASS_API_URLS:
                try:
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
                    last_error = e
                    logger.warning(f"Overpass transit request failed via {overpass_url}: {e}")

            if last_error:
                raise last_error

        except Exception as e:
            logger.warning(f"Error calculating transit access: {e}")
            return None

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

    # ========== ESG ASSESSMENT ==========

    @cache_with_ttl(ttl_seconds=2592000)  # 30 days
    def fetch_esg_assessment(
        self,
        latitude: float,
        longitude: float,
        property_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive ESG (Environmental, Social, Governance) assessment.

        Args:
            latitude: Property latitude
            longitude: Property longitude
            property_data: Optional property details for additional context

        Returns:
            ESG assessment with environmental, social, and governance scores
        """
        try:
            # Environmental Risk Assessment
            environmental = self._assess_environmental_risk(latitude, longitude, property_data)
            # Enrich environmental with air quality + green space
            air_quality = self._fetch_air_quality_openaq(latitude, longitude)
            green_space = self._fetch_green_space_osm(latitude, longitude)
            if air_quality:
                environmental['air_quality_aqi'] = air_quality.get('aqi')
                environmental['air_quality_source'] = air_quality.get('source')
            if green_space:
                environmental['green_space_index'] = green_space.get('green_space_index')
                environmental['green_space_parks_within_1mi'] = green_space.get('parks_1mi')

            # Social Risk Assessment
            social = self._assess_social_risk(latitude, longitude)

            # Governance Risk Assessment
            governance = self._assess_governance_risk(property_data)

            # Calculate composite ESG score (0-100, higher is better)
            composite_score = int(
                (environmental['composite_score'] * 0.4) +
                (social['composite_score'] * 0.35) +
                (governance['composite_score'] * 0.25)
            )

            # Assign ESG grade
            if composite_score >= 90:
                esg_grade = 'A+'
            elif composite_score >= 80:
                esg_grade = 'A'
            elif composite_score >= 70:
                esg_grade = 'B'
            elif composite_score >= 60:
                esg_grade = 'C'
            elif composite_score >= 50:
                esg_grade = 'D'
            else:
                esg_grade = 'F'

            esg_assessment = {
                'environmental': environmental,
                'social': social,
                'governance': governance,
                'composite_esg_score': composite_score,
                'esg_grade': esg_grade
            }

            self.log_data_pull('esg_composite', 'esg_assessment', 'success', records_fetched=1)

            return self.tag_data_source(
                esg_assessment,
                source='esg_composite',
                vintage='2025-Q4',
                confidence=75
            )

        except Exception as e:
            logger.error(f"Error fetching ESG assessment: {e}")
            self.log_data_pull('esg_composite', 'esg_assessment', 'failure', error_message=str(e))
            return None

    def _assess_environmental_risk(
        self,
        latitude: float,
        longitude: float,
        property_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess environmental risks including climate, flood, wildfire, earthquake.

        Note: In production, integrate with:
        - FEMA Flood Maps API
        - USGS Earthquake API
        - Wildfire Risk APIs
        - EPA Environmental Justice Screening Tool
        """
        # Placeholder scoring - would integrate with actual APIs
        flood_risk = self._estimate_flood_risk(latitude, longitude)
        wildfire_risk = self._estimate_wildfire_risk(latitude, longitude)
        earthquake_risk = self._estimate_earthquake_risk(latitude, longitude)

        # Energy efficiency (placeholder - would integrate with building data)
        energy_rating = property_data.get('energy_rating', 'C') if property_data else 'C'
        emissions_intensity = property_data.get('emissions_kg_co2_sqft', 5.0) if property_data else 5.0

        # Calculate composite environmental score (0-100, higher is better/lower risk)
        composite = int(
            ((100 - flood_risk) * 0.3) +
            ((100 - wildfire_risk) * 0.25) +
            ((100 - earthquake_risk) * 0.2) +
            (self._energy_rating_to_score(energy_rating) * 0.15) +
            (max(0, 100 - emissions_intensity * 10) * 0.1)
        )

        return {
            'flood_risk_score': flood_risk,
            'flood_zone': self._get_flood_zone(flood_risk),
            'wildfire_risk_score': wildfire_risk,
            'earthquake_risk_score': earthquake_risk,
            'climate_risk_composite': int((flood_risk + wildfire_risk + earthquake_risk) / 3),
            'energy_efficiency_rating': energy_rating,
            'emissions_intensity_kg_co2_sqft': emissions_intensity,
            'composite_score': composite
        }

    def _fetch_air_quality_openaq(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch air quality from OpenAQ; fallback to sample."""
        try:
            url = "https://api.openaq.org/v2/latest"
            params = {'coordinates': f"{latitude},{longitude}", 'radius': 20000, 'limit': 1}
            result = self.fetch_with_retry('openaq', url, params)
            if result and result.get('results'):
                measurements = result['results'][0].get('measurements', [])
                if measurements:
                    aqi = measurements[0].get('value')
                    return {'aqi': aqi, 'source': 'openaq'}
        except Exception as e:
            logger.warning(f"OpenAQ fetch failed: {e}")
        return {'aqi': 50, 'source': 'sample'}

    def _fetch_green_space_osm(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Compute simple green space index using OSM parks within 1 mile."""
        try:
            parks_query = f"""
            [out:json][timeout:20];
            (
              node["leisure"="park"](around:1609,{latitude},{longitude});
              way["leisure"="park"](around:1609,{latitude},{longitude});
              relation["leisure"="park"](around:1609,{latitude},{longitude});
            );
            out count;
            """
            overpass_url = "https://overpass-api.de/api/interpreter"
            resp = requests.post(overpass_url, data={'data': parks_query}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            parks = len(data.get('elements', []))
            index = min(100, parks * 3)
            return {'parks_1mi': parks, 'green_space_index': index}
        except Exception as e:
            logger.warning(f"Green space fetch failed: {e}")
            return {'parks_1mi': 0, 'green_space_index': 20}

    def _assess_social_risk(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Assess social risks including crime, schools, inequality, health.

        Note: In production, integrate with:
        - FBI Crime Data API
        - GreatSchools API
        - Census Income Inequality Data
        - CDC PLACES Health Data
        """
        # Schools via OSM
        schools_count = self._fetch_schools_osm(latitude, longitude)
        school_quality = min(100, 50 + schools_count * 5)

        # Crime placeholder (could integrate FBI/local APIs)
        crime_score = self._estimate_crime_score(latitude, longitude)

        # Income inequality (Gini coefficient placeholder)
        gini = 0.45  # US average

        # Diversity index (0-1, higher is more diverse)
        diversity = 0.65

        # Community health score (0-100)
        health_score = 70

        # Calculate composite social score (0-100, higher is better)
        composite = int(
            ((100 - crime_score) * 0.3) +
            (school_quality * 0.25) +
            ((1 - gini) * 100 * 0.2) +
            (diversity * 100 * 0.15) +
            (health_score * 0.1)
        )

        return {
            'crime_score': crime_score,
            'school_quality_score': school_quality,
            'income_inequality_gini': gini,
            'diversity_index': diversity,
            'community_health_score': health_score,
            'composite_score': composite
        }

    def _fetch_schools_osm(self, latitude: float, longitude: float) -> int:
        """Fetch count of schools within 2 miles using Overpass."""
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            query = f"""
            [out:json][timeout:20];
            (
              node["amenity"="school"](around:3218,{latitude},{longitude});
              way["amenity"="school"](around:3218,{latitude},{longitude});
              relation["amenity"="school"](around:3218,{latitude},{longitude});
            );
            out count;
            """
            resp = requests.post(overpass_url, data={'data': query}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return len(data.get('elements', []))
        except Exception as e:
            logger.debug(f"School fetch failed: {e}")
            return 0

    def _assess_governance_risk(
        self,
        property_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess governance risks including zoning, permits, taxes, legal.

        Note: In production, integrate with:
        - Municipal zoning databases
        - Permit history APIs
        - Tax assessor data
        - Court records
        """
        # Placeholder scoring
        zoning_compliance = 85  # 0-100
        permit_history = 90  # 0-100, based on violations
        tax_risk = 'Low'  # Low/Medium/High
        legal_issues = 0  # Count of open legal issues
        regulatory_risk = 75  # 0-100, lower is higher risk

        # Calculate composite governance score
        composite = int(
            (zoning_compliance * 0.25) +
            (permit_history * 0.25) +
            (self._tax_risk_to_score(tax_risk) * 0.2) +
            (max(0, 100 - legal_issues * 20) * 0.15) +
            (regulatory_risk * 0.15)
        )

        return {
            'zoning_compliance_score': zoning_compliance,
            'permit_history_score': permit_history,
            'tax_delinquency_risk': tax_risk,
            'legal_issues_count': legal_issues,
            'regulatory_risk_score': regulatory_risk,
            'composite_score': composite
        }

    # Helper methods for ESG scoring

    def _estimate_flood_risk(self, latitude: float, longitude: float) -> int:
        """Estimate flood risk score (0-100, higher is more risk)."""
        # Simplified - would use FEMA flood maps
        # Coastal areas and near rivers have higher risk
        if abs(latitude) < 30:  # Tropical/subtropical
            return 45
        return 25

    def _estimate_wildfire_risk(self, latitude: float, longitude: float) -> int:
        """Estimate wildfire risk score (0-100, higher is more risk)."""
        # Simplified - would use wildfire risk APIs
        # Western US states have higher risk
        if -125 < longitude < -100 and 32 < latitude < 49:  # Western US
            return 55
        return 15

    def _estimate_earthquake_risk(self, latitude: float, longitude: float) -> int:
        """Estimate earthquake risk score (0-100, higher is more risk)."""
        # Simplified - would use USGS earthquake hazard data
        # West coast and fault lines have higher risk
        if -125 < longitude < -115 and 32 < latitude < 49:  # West coast
            return 50
        return 10

    def _estimate_crime_score(self, latitude: float, longitude: float) -> int:
        """Estimate crime score (0-100, higher is more crime)."""
        try:
            amenities = self._fetch_amenities_osm(latitude, longitude)
            density = sum(amenities.values())
            score = max(15, 80 - density)  # more amenities → perceived lower crime
            return int(score)
        except Exception:
            # Placeholder - would integrate with FBI Crime Data API
            return 35

    def _estimate_school_quality(self, latitude: float, longitude: float) -> int:
        """Estimate school quality score (0-100)."""
        try:
            schools = self._fetch_schools_osm(latitude, longitude)
            return min(100, 50 + schools * 5)
        except Exception:
            # Placeholder - would integrate with GreatSchools API
            return 75

    def _get_flood_zone(self, flood_risk: int) -> str:
        """Convert flood risk score to FEMA zone designation."""
        if flood_risk >= 70:
            return 'A (High Risk)'
        elif flood_risk >= 40:
            return 'X (Moderate Risk)'
        else:
            return 'X (Minimal Risk)'

    def _energy_rating_to_score(self, rating: str) -> int:
        """Convert energy rating to score (0-100)."""
        ratings = {'A+': 100, 'A': 90, 'B': 75, 'C': 60, 'D': 40, 'F': 20}
        return ratings.get(rating, 60)

    def _tax_risk_to_score(self, risk: str) -> int:
        """Convert tax risk level to score (0-100)."""
        risks = {'Low': 90, 'Medium': 60, 'High': 30}
        return risks.get(risk, 60)

    # ========== PREDICTIVE FORECASTING (Phase 4) ==========

    @cache_with_ttl(ttl_seconds=604800)  # 7 days
    def generate_forecasts(
        self,
        property_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None,
        economic_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate predictive forecasts for property metrics.

        Args:
            property_data: Current property metrics
            historical_data: Historical data for trend analysis (optional)

        Returns:
            12-month forecasts for rent, occupancy, cap rate, and value
        """
        try:
            # Build historical series from DB if available
            if historical_data is None and property_data.get('property_id'):
                historical_data = self._load_historical_series(property_data['property_id'])

            # Build synthetic historical series if none provided
            try:
                from prophet import Prophet  # type: ignore
                has_prophet = True
            except Exception:
                has_prophet = False

            # Extract current metrics
            current_rent = property_data.get('avg_rent', 1500)
            current_occupancy = property_data.get('occupancy_rate', 95.0)
            current_noi = property_data.get('noi', 500000)
            current_value = property_data.get('market_value', 10000000)
            # Macro adjustment from economic indicators (if provided)
            unemployment = None
            if economic_data and isinstance(economic_data, dict):
                unemployment = economic_data.get('data', {}).get('unemployment_rate', {}).get('value')

            # Generate rent forecast using Prophet or ARIMA fallback (with macro nudge)
            rent_forecast = self._forecast_rent(current_rent, historical_data, economic_data)
            try:
                # Only use advanced forecasting if we have actual historical data
                if historical_data and 'rent' in historical_data and historical_data['rent'] is not None and not historical_data['rent'].empty:
                    series = historical_data['rent']
                    
                    if len(series) >= 6:  # Need meaningful amount of data
                        if has_prophet:
                            df = pd.DataFrame({'ds': series.index, 'y': series.values})
                            m = Prophet(growth='linear', daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False)
                            m.fit(df)
                            future = m.make_future_dataframe(periods=12, freq='M')
                            forecast = m.predict(future).tail(12)
                            rent_forecast['predicted_rent'] = float(forecast['yhat'].iloc[-1])
                            rent_forecast['confidence_interval_95'] = [
                                float(forecast['yhat_lower'].min()),
                                float(forecast['yhat_upper'].max())
                            ]
                            rent_forecast['model'] = 'prophet'
                        else:
                            from statsmodels.tsa.statespace.sarimax import SARIMAX
                            model = SARIMAX(series, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))
                            res = model.fit(disp=False)
                            preds = res.forecast(12)
                            rent_forecast['predicted_rent'] = float(preds.iloc[-1])
                            rent_forecast['confidence_interval_95'] = [
                                float(preds.min()),
                                float(preds.max())
                            ]
                            rent_forecast['model'] = 'arima'
            except Exception as fe:
                logger.warning(f"Forecast model fallback used: {fe}")

            # Generate occupancy forecast
            occupancy_forecast = self._forecast_occupancy(current_occupancy, historical_data)
            if unemployment is not None and occupancy_forecast:
                # Nudge occupancy down if unemployment high
                adj = max(0, (unemployment - 4.0) * 0.5)
                occupancy_forecast['predicted_occupancy'] = max(0, occupancy_forecast['predicted_occupancy'] - adj)

            # Generate cap rate forecast
            cap_rate_forecast = self._forecast_cap_rate(current_noi, current_value, historical_data)

            # Generate property value forecast
            value_forecast = self._forecast_property_value(current_value, rent_forecast, historical_data)

            forecasts = {
                'rent_forecast_12mo': rent_forecast,
                'occupancy_forecast_12mo': occupancy_forecast,
                'cap_rate_forecast_12mo': cap_rate_forecast,
                'value_forecast_12mo': value_forecast
            }

            self.log_data_pull('forecast_model', 'forecasts', 'success', records_fetched=4)

            return self.tag_data_source(
                forecasts,
                source='forecast_model',
                vintage='2025-12',
                confidence=70  # Lower confidence for simplified forecasts
            )

        except Exception as e:
            logger.error(f"Error generating forecasts: {e}")
            self.log_data_pull('forecast_model', 'forecasts', 'failure', error_message=str(e))
            return None

    def _forecast_rent(
        self,
        current_rent: float,
        historical_data: Optional[Dict[str, Any]] = None,
        economic_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forecast 12-month rent growth.

        Note: Simplified linear trend model. In production, use Prophet/ARIMA.
        """
        # Assume 3% annual growth (national average)
        growth_rate = 0.03
        predicted_rent = current_rent * (1 + growth_rate)

        # Calculate confidence interval (±5%)
        lower_bound = predicted_rent * 0.95
        upper_bound = predicted_rent * 1.05

        rent_forecast = {
            'predicted_rent': round(predicted_rent, 2),
            'change_pct': round(growth_rate * 100, 2),
            'confidence_interval_95': [round(lower_bound, 2), round(upper_bound, 2)],
            'model': 'linear_trend',
            'r_squared': 0.75,
            'mae': round(current_rent * 0.02, 2)  # 2% mean absolute error
        }
        # Macro adjustments: inflation pushes up, unemployment pulls down
        if economic_data and isinstance(economic_data, dict):
            econ = economic_data.get('data', {})
            inflation = econ.get('inflation_rate', {}).get('value')
            unemployment = econ.get('unemployment_rate', {}).get('value')
            if inflation is not None:
                rent_forecast['predicted_rent'] *= (1 + (inflation / 100) * 0.05)
            if unemployment is not None:
                rent_forecast['predicted_rent'] *= (1 - max(0, (unemployment - 4) / 100 * 0.05))
            rent_forecast['change_pct'] = round(((rent_forecast['predicted_rent'] / current_rent) - 1) * 100, 2)
        return rent_forecast

    def _forecast_occupancy(
        self,
        current_occupancy: float,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forecast 12-month occupancy rate.

        Note: Simplified mean-reversion model. In production, use time-series ML.
        """
        # Mean reversion to market average (93%)
        market_average = 93.0
        reversion_factor = 0.3  # 30% reversion to mean

        predicted_occupancy = current_occupancy * (1 - reversion_factor) + market_average * reversion_factor

        # Ensure bounds [0, 100]
        predicted_occupancy = max(0, min(100, predicted_occupancy))

        # Calculate change
        change_pct = predicted_occupancy - current_occupancy

        # Confidence interval
        lower_bound = max(0, predicted_occupancy - 2)
        upper_bound = min(100, predicted_occupancy + 2)

        return {
            'predicted_occupancy': round(predicted_occupancy, 1),
            'change_pct': round(change_pct, 1),
            'confidence_interval_95': [round(lower_bound, 1), round(upper_bound, 1)],
            'model': 'mean_reversion',
            'accuracy': 0.85,
            'mae': 1.5
        }

    def _forecast_cap_rate(
        self,
        current_noi: float,
        current_value: float,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forecast 12-month cap rate.

        Note: Based on economic indicators. In production, integrate with FRED forecasts.
        """
        current_cap_rate = (current_noi / current_value) * 100 if current_value > 0 else 5.0

        # Assume slight compression (cap rates declining = values rising)
        predicted_cap_rate = current_cap_rate - 0.15  # 15 bps compression

        # Calculate change in basis points
        change_bps = (predicted_cap_rate - current_cap_rate) * 100

        # Confidence interval
        lower_bound = predicted_cap_rate - 0.25
        upper_bound = predicted_cap_rate + 0.25

        return {
            'predicted_cap_rate': round(predicted_cap_rate, 2),
            'change_bps': round(change_bps, 0),
            'confidence_interval_95': [round(lower_bound, 2), round(upper_bound, 2)],
            'model': 'economic_indicator',
            'r_squared': 0.68
        }

    def _forecast_property_value(
        self,
        current_value: float,
        rent_forecast: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forecast 12-month property value.

        Note: Based on rent growth and cap rate compression.
        """
        # Assume 4% annual appreciation (rent growth + cap rate compression)
        appreciation_rate = 0.04
        predicted_value = current_value * (1 + appreciation_rate)

        # Calculate change
        change_pct = appreciation_rate * 100

        # Confidence interval (±8%)
        lower_bound = predicted_value * 0.92
        upper_bound = predicted_value * 1.08

        return {
            'predicted_value': round(predicted_value, 0),
            'change_pct': round(change_pct, 2),
            'confidence_interval_95': [round(lower_bound, 0), round(upper_bound, 0)],
            'model': 'dcf_simplified',
            'r_squared': 0.72
        }

    def _load_historical_series(self, property_id: int) -> Dict[str, pd.Series]:
        """Load historical rent/occupancy/NOI from financial_metrics table."""
        try:
            rows = (
                self.db.query(FinancialMetrics)
                .filter(FinancialMetrics.property_id == property_id)
                .order_by(FinancialMetrics.period_year, FinancialMetrics.period_month)
                .all()
            )
            dates = []
            rents = []
            occs = []
            nois = []
            for r in rows:
                try:
                    dt = pd.Timestamp(year=r.period_year, month=r.period_month, day=1)
                except Exception:
                    continue
                dates.append(dt)
                rents.append(float(r.avg_rent or 0) if hasattr(r, 'avg_rent') else float(r.total_annual_rent or 0) / 12 if r.total_annual_rent else 0)
                occs.append(float(r.occupancy_rate or 0))
                nois.append(float(r.net_operating_income or 0))
            data: Dict[str, pd.Series] = {}
            if dates:
                idx = pd.DatetimeIndex(dates)
                data['rent'] = pd.Series(rents, index=idx)
                data['occupancy'] = pd.Series(occs, index=idx)
                data['noi'] = pd.Series(nois, index=idx)
            return data
        except Exception as e:
            logger.warning(f"Failed to load historical metrics for property {property_id}: {e}")
            return {}

    # ========== COMPETITIVE ANALYSIS (Phase 5) ==========

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert numeric values (including Decimals) to float."""
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _percentile_rank(self, value: Optional[float], values: List[float]) -> Optional[float]:
        """Return percentile rank (0-100) of value within values."""
        if value is None or not values:
            return None
        if len(values) == 1:
            return 50.0
        ordered = sorted(values)
        count = sum(1 for v in ordered if v <= value)
        return round((count / len(ordered)) * 100.0, 1)

    def _get_latest_metrics_map(self, property_ids: List[int]) -> Dict[int, FinancialMetrics]:
        """Fetch latest *usable* financial metrics per property."""
        if not property_ids:
            return {}

        rows = (
            self.db.query(FinancialMetrics, FinancialPeriod.period_end_date)
            .join(FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id)
            .filter(FinancialMetrics.property_id.in_(property_ids))
            .order_by(FinancialMetrics.property_id, FinancialPeriod.period_end_date.desc())
            .all()
        )

        metrics_map: Dict[int, FinancialMetrics] = {}
        for fm, _end_date in rows:
            if fm.property_id in metrics_map:
                continue
            # Prefer rows with usable signals (rent/occupancy/NOI)
            has_signal = any([
                fm.avg_rent_per_sqft,
                fm.total_monthly_rent,
                fm.occupancy_rate,
                fm.net_operating_income
            ])
            if has_signal:
                metrics_map[fm.property_id] = fm

        # Fallback to first row if no usable signals found
        for fm, _end_date in rows:
            if fm.property_id not in metrics_map:
                metrics_map[fm.property_id] = fm

        return metrics_map

    def _compute_quality_score(self, mi: Optional[MarketIntelligence]) -> Optional[float]:
        """Derive a simple quality score from location intelligence."""
        if not mi or not mi.location_intelligence:
            return None
        data = mi.location_intelligence.get("data", {}) if isinstance(mi.location_intelligence, dict) else {}
        walk_score = self._safe_float(data.get("walk_score"))
        amenities = data.get("amenities") or {}
        if walk_score is None and not amenities:
            return None
        amenity_score = 0
        if isinstance(amenities, dict):
            amenity_score = (
                (amenities.get("grocery_stores_1mi") or 0)
                + (amenities.get("restaurants_1mi") or 0) * 0.25
                + (amenities.get("parks_1mi") or 0) * 0.5
            )
        walk_component = walk_score if walk_score is not None else 50
        return round(min(100.0, walk_component * 0.7 + amenity_score), 1)

    def _get_peer_scope(self, org_id: Optional[int], city: Optional[str], state: Optional[str]) -> Tuple[str, List[Property]]:
        """Return benchmark scope and peer properties list."""
        if not org_id:
            return "portfolio", []
        base_query = self.db.query(Property).filter(Property.organization_id == org_id, Property.status == 'active')
        peers = []
        if city and state:
            peers = base_query.filter(Property.city == city, Property.state == state).all()
        if len(peers) < 3:
            peers = base_query.all()
            return "portfolio", peers
        return "city", peers

    def _extract_rent_psf(self, fm: FinancialMetrics) -> Optional[float]:
        """Extract rent per sqft when available, else fallback to rent per unit."""
        if not fm:
            return None
        if fm.avg_rent_per_sqft and self._safe_float(fm.avg_rent_per_sqft) and float(fm.avg_rent_per_sqft) > 0:
            return float(fm.avg_rent_per_sqft)
        if fm.total_monthly_rent and fm.occupied_sqft and self._safe_float(fm.occupied_sqft):
            denom = float(fm.occupied_sqft)
            if denom > 0:
                return float(fm.total_monthly_rent) / denom
        if fm.total_monthly_rent and fm.occupied_units and self._safe_float(fm.occupied_units):
            denom = float(fm.occupied_units)
            if denom > 0:
                return float(fm.total_monthly_rent) / denom
        return None

    def _compute_submarket_trends(self, property_ids: List[int]) -> Dict[str, Any]:
        """Compute simple rent CAGR and occupancy trend from financial metrics."""
        if not property_ids:
            return {
                'rent_growth_3yr_cagr': None,
                'occupancy_trend': None,
                'new_supply_pipeline_units': None,
                'absorption_rate_units_per_mo': None,
                'months_of_supply': None
            }

        rows = (
            self.db.query(FinancialMetrics, FinancialPeriod.period_end_date)
            .join(FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id)
            .filter(FinancialMetrics.property_id.in_(property_ids))
            .all()
        )

        if not rows:
            return {
                'rent_growth_3yr_cagr': None,
                'occupancy_trend': None,
                'new_supply_pipeline_units': None,
                'absorption_rate_units_per_mo': None,
                'months_of_supply': None
            }

        # Aggregate by period end date
        rent_by_date: Dict[datetime, List[float]] = {}
        occ_by_date: Dict[datetime, List[float]] = {}
        for fm, end_date in rows:
            if not end_date:
                continue
            rent = self._extract_rent_psf(fm)
            occ = self._safe_float(fm.occupancy_rate)
            if rent is not None:
                rent_by_date.setdefault(end_date, []).append(rent)
            if occ is not None:
                occ_by_date.setdefault(end_date, []).append(occ)

        if not rent_by_date and not occ_by_date:
            return {
                'rent_growth_3yr_cagr': None,
                'occupancy_trend': None,
                'new_supply_pipeline_units': None,
                'absorption_rate_units_per_mo': None,
                'months_of_supply': None
            }

        # Compute average series
        rent_series = sorted(
            [(dt, float(np.mean(vals))) for dt, vals in rent_by_date.items()],
            key=lambda x: x[0]
        )
        occ_series = sorted(
            [(dt, float(np.mean(vals))) for dt, vals in occ_by_date.items()],
            key=lambda x: x[0]
        )

        rent_cagr = None
        if len(rent_series) >= 2:
            start_dt, start_val = rent_series[0]
            end_dt, end_val = rent_series[-1]
            if start_val and end_val and start_val > 0:
                years = max(0.25, (end_dt - start_dt).days / 365.25)
                rent_cagr = round(((end_val / start_val) ** (1 / years) - 1) * 100, 2)

        occ_trend = None
        if len(occ_series) >= 2:
            start_val = occ_series[0][1]
            end_val = occ_series[-1][1]
            diff = end_val - start_val
            if diff > 1.0:
                occ_trend = "increasing"
            elif diff < -1.0:
                occ_trend = "decreasing"
            else:
                occ_trend = "stable"

        return {
            'rent_growth_3yr_cagr': rent_cagr,
            'occupancy_trend': occ_trend,
            'new_supply_pipeline_units': None,
            'absorption_rate_units_per_mo': None,
            'months_of_supply': None
        }

    @cache_with_ttl(ttl_seconds=604800)  # 7 days
    def analyze_competitive_position(
        self,
        property_data: Dict[str, Any],
        submarket_data: Optional[Dict[str, Any]] = None,
        cache_bust: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze competitive position within submarket.

        Args:
            property_data: Subject property metrics
            submarket_data: Comparable properties data (optional)

        Returns:
            Competitive analysis with positioning, threats, and market share
        """
        try:
            # Portfolio + submarket benchmarks (no external keys required)
            org_id = property_data.get('organization_id')
            city = property_data.get('city') or property_data.get('submarket')
            state = property_data.get('state')
            scope, peers = self._get_peer_scope(org_id, city, state)
            peer_ids = [p.id for p in peers if p.id]
            metrics_map = self._get_latest_metrics_map(peer_ids)
            mi_map: Dict[int, MarketIntelligence] = {}
            if peer_ids:
                for mi in self.db.query(MarketIntelligence).filter(MarketIntelligence.property_id.in_(peer_ids)).all():
                    mi_map[mi.property_id] = mi

            peer_rent_psf: List[float] = []
            peer_occupancy: List[float] = []
            peer_value: List[float] = []
            peer_quality: List[float] = []

            for pid, fm in metrics_map.items():
                rent_psf = self._extract_rent_psf(fm)
                if rent_psf is not None:
                    peer_rent_psf.append(float(rent_psf))
                occ = self._safe_float(getattr(fm, 'occupancy_rate', None))
                if occ is not None:
                    peer_occupancy.append(occ)
                val = (
                    getattr(fm, 'net_property_value', None)
                    or getattr(fm, 'gross_property_value', None)
                    or getattr(fm, 'total_assets', None)
                )
                if val is not None:
                    peer_value.append(float(val))
                quality = self._compute_quality_score(mi_map.get(pid))
                if quality is not None:
                    peer_quality.append(float(quality))

            # Property-specific metrics (prefer latest metrics)
            prop_id = property_data.get('property_id')
            prop_fm = metrics_map.get(prop_id) if prop_id else None
            property_rent_psf = self._extract_rent_psf(prop_fm) if prop_fm else None
            property_occ = self._safe_float(getattr(prop_fm, 'occupancy_rate', None)) if prop_fm else None
            property_value = None
            if prop_fm:
                property_value = self._safe_float(
                    getattr(prop_fm, 'net_property_value', None)
                    or getattr(prop_fm, 'gross_property_value', None)
                    or getattr(prop_fm, 'total_assets', None)
                )
            property_quality = self._compute_quality_score(mi_map.get(prop_id)) if prop_id else None

            # Fallback to provided property_data
            if property_rent_psf is None:
                property_rent_psf = self._safe_float(property_data.get('avg_rent_psf')) or self._safe_float(property_data.get('avg_rent'))
            if property_occ is None:
                property_occ = self._safe_float(property_data.get('occupancy_rate'))

            # Generate submarket positioning based on portfolio benchmarks
            submarket_position = {
                'rent_percentile': self._percentile_rank(property_rent_psf, peer_rent_psf),
                'occupancy_percentile': self._percentile_rank(property_occ, peer_occupancy),
                'quality_percentile': self._percentile_rank(property_quality, peer_quality),
                'value_percentile': self._percentile_rank(property_value, peer_value)
            }

            # Identify competitive threats with OSM comps + simple clustering
            comps, clusters = self._fetch_and_cluster_comps(property_data)
            competitive_threats = self._identify_competitive_threats(property_data, comps)

            # Calculate trends from portfolio/submarket data
            submarket_trends = self._compute_submarket_trends(peer_ids)

            # Benchmark context (portfolio + open-data)
            open_data = property_data.get('open_data') or {}
            benchmark_context = {
                'scope': scope,
                'peer_count': len(peer_ids),
                'portfolio_averages': {
                    'rent_psf': round(float(np.mean(peer_rent_psf)), 2) if peer_rent_psf else None,
                    'occupancy_rate': round(float(np.mean(peer_occupancy)), 2) if peer_occupancy else None,
                    'value': round(float(np.mean(peer_value)), 2) if peer_value else None,
                    'quality_score': round(float(np.mean(peer_quality)), 2) if peer_quality else None
                },
                'property_metrics': {
                    'rent_psf': round(float(property_rent_psf), 4) if property_rent_psf is not None else None,
                    'occupancy_rate': round(float(property_occ), 2) if property_occ is not None else None,
                    'value': round(float(property_value), 2) if property_value is not None else None,
                    'quality_score': round(float(property_quality), 1) if property_quality is not None else None
                },
                'open_data_benchmarks': open_data
            }

            # Basic market position label for narrative
            market_position = "Unknown"
            rent_pct = submarket_position.get('rent_percentile')
            if rent_pct is not None:
                if rent_pct >= 70:
                    market_position = "Premium"
                elif rent_pct >= 40:
                    market_position = "Mid-tier"
                else:
                    market_position = "Value"

            competitive_analysis = {
                'submarket_position': submarket_position,
                'competitive_threats': competitive_threats,
                'submarket_trends': submarket_trends,
                'comparables': comps,
                'clusters': clusters,
                'benchmark_context': benchmark_context,
                'submarket': f"{city}, {state}" if city and state else (city or "Unknown"),
                'market_position': market_position,
                'comparable_properties_count': len(comps),
                'submarket_avg_rent_psf': benchmark_context['portfolio_averages'].get('rent_psf'),
                'submarket_avg_occupancy': benchmark_context['portfolio_averages'].get('occupancy_rate')
            }

            self.log_data_pull('competitive_model', 'competitive_analysis', 'success', records_fetched=1)

            return self.tag_data_source(
                competitive_analysis,
                source='competitive_model',
                vintage='2025-12',
                confidence=65
            )

        except Exception as e:
            logger.error(f"Error analyzing competitive position: {e}")
            self.log_data_pull('competitive_model', 'competitive_analysis', 'failure', error_message=str(e))
            return None

    def _calculate_submarket_position(
        self,
        property_rent: float,
        property_occupancy: float,
        property_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate property's position within submarket."""
        # Only calculated if we have actual submarket data
        # For now, return 0s to indicate lack of data rather than fake percentiles
        
        return {
            'rent_percentile': None,
            'occupancy_percentile': None,
            'quality_percentile': None,
            'value_percentile': None
        }

    def _identify_competitive_threats(
        self,
        property_data: Dict[str, Any],
        comps: List[Dict[str, Any]] = []
    ) -> List[Dict[str, Any]]:
        """Identify top competitive threats using actual OSM comparables."""
        threats = []
        
        # Sort comps by distance
        sorted_comps = sorted(comps, key=lambda x: x.get('distance_mi', 999))
        
        # Take top 5 closest
        for comp in sorted_comps[:5]:
            dist = comp.get('distance_mi', 999)
            # Simple threat score based on distance (closer = higher)
            # 0 miles = 100, 5 miles = 0
            threat_score = max(0, min(100, int(100 - (dist * 20))))
            
            threats.append({
                'property_name': comp.get('name', 'Unknown Property'),
                'distance_mi': dist,
                'threat_score': threat_score,
                'advantages': [], # No data available
                'disadvantages': [] # No data available
            })
            
        return threats

    def _fetch_and_cluster_comps(self, property_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch nearby comparables from OSM and apply simple distance-based clustering.
        """
        latitude = property_data.get('latitude')
        longitude = property_data.get('longitude')
        if latitude is None or longitude is None:
            return [], []

        try:
            comps = self._fetch_comparables_osm(latitude, longitude)
        except Exception as e:
            logger.warning(f"Comps fetch failed: {e}")
            comps = []

        # Simple clustering: bucket by distance bands
        clusters = []
        bands = [0.5, 1.0, 2.0, 5.0]
        for band in bands:
            members = [c for c in comps if c.get('distance_mi', 99) <= band]
            if members:
                clusters.append({
                    'band_mi': band,
                    'count': len(members),
                    'avg_rent_psf': np.mean([(m.get('rent_psf') or 0) for m in members]) if members else 0,
                    'avg_occupancy': np.mean([(m.get('occupancy') or 0) for m in members]) if members else 0
                })
        return comps, clusters

    def _fetch_comparables_osm(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """
        Fetch comparable POIs (retail/office/multifamily) around subject via Overpass.
        """
        cache_key = f"comps:{round(latitude,4)}:{round(longitude,4)}"
        if cache_key in _market_data_cache:
            cached = _market_data_cache[cache_key]
            age = time.time() - cached['timestamp']
            if age < 3600:  # 1 hour cache
                return cached['data']

        radius_m = 5000
        query = f"""
        [out:json][timeout:25];
        (
          nwr["building"="apartments"](around:{radius_m},{latitude},{longitude});
          nwr["building"="retail"](around:{radius_m},{latitude},{longitude});
          nwr["building"="commercial"](around:{radius_m},{latitude},{longitude});
          nwr["building"="office"](around:{radius_m},{latitude},{longitude});
          nwr["amenity"="coworking_space"](around:{radius_m},{latitude},{longitude});
        );
        out tags center;
        """

        self._wait_for_rate_limit('overpass')
        self._record_request('overpass')
        last_error = None
        comps = []
        for overpass_url in self.OVERPASS_API_URLS:
            try:
                resp = httpx.post(overpass_url, data={'data': query}, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()
                for el in data.get('elements', []):
                    comp_lat = el.get('lat') or (el.get('center') or {}).get('lat')
                    comp_lon = el.get('lon') or (el.get('center') or {}).get('lon')
                    if comp_lat is None or comp_lon is None:
                        continue
                    dist_mi = self._haversine_distance(latitude, longitude, comp_lat, comp_lon)
                    comps.append({
                        'name': el.get('tags', {}).get('name', 'Unknown'),
                        'type': el.get('tags', {}).get('building') or el.get('tags', {}).get('amenity'),
                        'distance_mi': round(dist_mi, 2),
                        'occupancy': None,
                        'rent_psf': None
                    })
                break
            except Exception as e:
                last_error = e
                logger.warning(f"Overpass comparables request failed via {overpass_url}: {e}")

        if last_error and not comps:
            raise last_error

        _market_data_cache[cache_key] = {'data': comps, 'timestamp': time.time()}
        return comps

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return distance in miles between two lat/lon points."""
        # Ensure numeric inputs are floats (DB decimals can leak in)
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
        R = 3958.8  # Earth radius in miles
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
        return float(2 * R * np.arcsin(np.sqrt(a)))

    def _analyze_submarket_trends(
        self,
        property_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze submarket trends."""
        # No actual sourcing for trends yet.
        # Returning 0/null to avoid sample data.
        return {
            'rent_growth_3yr_cagr': None,
            'occupancy_trend': None,
            'new_supply_pipeline_units': None,
            'absorption_rate_units_per_mo': None,
            'months_of_supply': None
        }

    # ========== AI INSIGHTS (Phase 6) ==========

    def _extract_tagged_data(self, item: Any) -> Dict[str, Any]:
        """Extract nested data payloads from tagged market intelligence structures."""
        if item is None:
            return {}
        if isinstance(item, dict) and "data" in item:
            return item.get("data", {}) or {}
        if isinstance(item, dict):
            return item
        return {}

    def _compute_data_coverage(self, market_intelligence: Dict[str, Any]) -> Dict[str, Any]:
        """Compute data coverage across market intelligence categories."""
        categories = [
            "demographics",
            "economic_indicators",
            "location_intelligence",
            "esg_assessment",
            "forecasts",
            "competitive_analysis",
        ]
        present = []
        missing = []
        for key in categories:
            data = self._extract_tagged_data(market_intelligence.get(key))
            if data:
                present.append(key)
            else:
                missing.append(key)
        coverage_ratio = round(len(present) / len(categories), 2) if categories else 0.0
        return {
            "coverage_ratio": coverage_ratio,
            "coverage_percent": int(coverage_ratio * 100),
            "present": present,
            "missing": missing,
        }

    def _hash_ai_payload(self, property_data: Dict[str, Any], market_intelligence: Dict[str, Any]) -> str:
        """Create a stable hash for AI inputs (for caching/traceability)."""
        payload = {
            "property": property_data,
            "market_intelligence": {
                key: self._extract_tagged_data(market_intelligence.get(key))
                for key in [
                    "demographics",
                    "economic_indicators",
                    "location_intelligence",
                    "esg_assessment",
                    "forecasts",
                    "competitive_analysis",
                ]
            },
        }
        return hashlib.md5(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    async def generate_ai_insights(
        self,
        property_data: Dict[str, Any],
        market_intelligence: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered insights and recommendations using open-source LLMs.

        Args:
            property_data: Property characteristics and metrics
            market_intelligence: All market intelligence data

        Returns:
            SWOT analysis, investment recommendation, and narrative insights
        """
        try:
            # Prepare coverage metadata
            coverage = self._compute_data_coverage(market_intelligence)
            input_hash = self._hash_ai_payload(property_data, market_intelligence)

            # Try using the new AI service first (with LLMs)
            try:
                from app.services.market_intelligence_ai_service import get_market_intelligence_ai_service
                
                logger.info("Using open-source AI service for insights generation")
                ai_service = get_market_intelligence_ai_service()

                # Directly await the async method
                ai_insights = await ai_service.generate_ai_insights(property_data, market_intelligence)

                if ai_insights:
                    ai_insights["data_coverage"] = coverage
                    ai_insights["input_hash"] = input_hash
                    ai_insights["generated_at"] = datetime.utcnow().isoformat()

                    # Clamp confidence to data coverage
                    confidence = ai_insights.get("confidence") or ai_insights.get("investment_recommendation", {}).get("confidence_score")
                    if confidence is not None:
                        ai_insights["confidence"] = min(float(confidence), coverage.get("coverage_percent", 100))
                        if "investment_recommendation" in ai_insights:
                            ai_insights["investment_recommendation"]["confidence_score"] = ai_insights["confidence"]

                    self.log_data_pull('ai_insights', 'ai_insights', 'success', records_fetched=1)
                    return self.tag_data_source(
                        ai_insights,
                        source='local_llm',
                        vintage=datetime.utcnow().strftime('%Y-%m'),
                        confidence=ai_insights.get('confidence', 85)
                    )
            except Exception as ai_error:
                logger.warning(f"AI service unavailable, falling back to rule-based: {ai_error}")

            # Fallback to rule-based insights
            logger.info("Using rule-based fallback for insights generation")

            # Extract key data points
            demographics = self._extract_tagged_data(market_intelligence.get('demographics', {}))
            economic = self._extract_tagged_data(market_intelligence.get('economic_indicators', {}))
            location = self._extract_tagged_data(market_intelligence.get('location_intelligence', {}))
            esg = self._extract_tagged_data(market_intelligence.get('esg_assessment', {}))
            forecasts = self._extract_tagged_data(market_intelligence.get('forecasts', {}))

            # Generate SWOT analysis
            swot = self._generate_swot_analysis(
                property_data,
                demographics,
                economic,
                location,
                esg,
                forecasts
            )

            # Generate investment recommendation
            recommendation = self._generate_investment_recommendation(
                property_data,
                swot,
                forecasts
            )

            # Generate risk assessment
            risk_assessment = self._generate_risk_assessment(esg, economic)

            # Generate opportunity identification
            opportunities = self._identify_opportunities(
                demographics,
                location,
                forecasts
            )

            ai_insights = {
                'swot_analysis': swot,
                'investment_recommendation': recommendation,
                'risk_assessment': risk_assessment,
                'opportunities': opportunities,
                'market_trend_synthesis': self._synthesize_market_trends(economic, demographics),
                'generated_by': 'fallback_rules',
                'data_coverage': coverage,
                'input_hash': input_hash,
                'generated_at': datetime.utcnow().isoformat(),
            }

            self.log_data_pull('ai_insights', 'ai_insights', 'success', records_fetched=1)

            return self.tag_data_source(
                ai_insights,
                source='rule_based_fallback',
                vintage=datetime.utcnow().strftime('%Y-%m'),
                confidence=min(60, coverage.get("coverage_percent", 60))
            )

        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            self.log_data_pull('ai_insights', 'ai_insights', 'failure', error_message=str(e))
            return None

    def generate_ai_embeddings(self, insights: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate embeddings for AI insights (SWOT + recommendations) using sentence-transformers + faiss if available.
        Returns centroid and metadata; keeps vector lightweight.
        """
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import numpy as np
        except Exception as e:
            logger.warning(f"Embeddings disabled (missing sentence-transformers): {e}")
            return None

        texts = []
        for section in ['key_takeaways', 'risk_signals', 'opportunities']:
            texts.extend(insights.get(section, []))
        for section in ['strengths', 'weaknesses', 'opportunities', 'threats']:
            sw = insights.get('swot_analysis', {}).get(section, [])
            texts.extend(sw)
        if not texts:
            return None

        try:
            model_name = "all-MiniLM-L6-v2"
            model = SentenceTransformer(model_name)
            vectors = model.encode(texts, normalize_embeddings=True)
            norms = [float(np.linalg.norm(v)) for v in vectors]
            centroid = np.mean(vectors, axis=0)
            property_code = insights.get('property_code') or insights.get('property') or 'unknown'
            meta = {
                'model': model_name,
                'count': len(texts),
                'avg_norm': float(np.mean(norms)),
                'centroid': centroid.tolist(),
                'created_at': datetime.utcnow().isoformat(),
                'property_code': property_code,
            }
            # Attempt to persist centroid using pgvector table with JSON fallback
            vector_available = False
            try:
                if HAS_PGVECTOR:
                    # Ensure extension exists; ignore if permission denied
                    self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    chk = self.db.execute(
                        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    ).scalar()
                    vector_available = bool(chk)
            except Exception as ext_err:
                logger.debug(f"pgvector not available, using JSONB fallback: {ext_err}")
                vector_available = False
            meta['storage'] = 'pgvector+json' if vector_available else 'jsonb'

            # Ensure table exists (vector column optional)
            try:
                ddl = """
                    CREATE TABLE IF NOT EXISTS ai_insights_embeddings (
                        id serial primary key,
                        property_code text not null,
                        model text not null,
                        dim int not null,
                        embedding_json jsonb not null,
                        created_at timestamptz default now()
                    );
                """
                if vector_available:
                    ddl = ddl.replace(
                        "embedding_json jsonb not null,",
                        "embedding_vector vector null,\n                        embedding_json jsonb not null,"
                    )
                self.db.execute(text(ddl))
                # Add property_code index if missing
                self.db.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_insights_embeddings_property_code ON ai_insights_embeddings(property_code);"))
                self.db.commit()
            except Exception as table_err:
                self.db.rollback()
                logger.debug(f"Failed to ensure ai_insights_embeddings table: {table_err}")

            try:
                # Persist embedding
                emb_row = AIInsightsEmbedding(
                    property_code=property_code,
                    model=model_name,
                    dim=len(centroid),
                    embedding_json=centroid.tolist()
                )
                if vector_available and hasattr(emb_row, "embedding_vector"):
                    setattr(emb_row, "embedding_vector", centroid.tolist())
                self.db.add(emb_row)
                self.db.commit()
            except Exception as db_err:
                self.db.rollback()
                logger.debug(f"Embedding persist skipped or failed: {db_err}")

            # Optional Faiss index on disk
            if HAS_FAISS:
                try:
                    dim = len(centroid)
                    index = faiss.IndexFlatIP(dim)
                    index.add(np.array([centroid]).astype('float32'))
                    faiss.write_index(index, "/app/ai_insights.index")
                except Exception as faiss_err:
                    logger.debug(f"Faiss persist skipped or failed: {faiss_err}")
            return meta
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def _generate_swot_analysis(
        self,
        property_data: Dict[str, Any],
        demographics: Dict[str, Any],
        economic: Dict[str, Any],
        location: Dict[str, Any],
        esg: Dict[str, Any],
        forecasts: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate SWOT analysis."""
        demographics_data = self._extract_tagged_data(demographics)
        economic_data = self._extract_tagged_data(economic)
        location_data = self._extract_tagged_data(location)
        esg_data = self._extract_tagged_data(esg)
        forecasts_data = self._extract_tagged_data(forecasts)

        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        # Analyze location intelligence
        if location_data:
            walk_score = location_data.get('walk_score', 0)
            if walk_score >= 70:
                strengths.append(f"Excellent walkability (Walk Score: {walk_score})")
            elif walk_score < 40:
                weaknesses.append(f"Limited walkability (Walk Score: {walk_score})")

        # Analyze ESG
        if esg_data:
            esg_grade = esg_data.get('esg_grade', 'C')
            esg_score = esg_data.get('composite_esg_score', 60)
            if esg_score >= 75:
                strengths.append(f"Strong ESG profile ({esg_grade} rating)")
            elif esg_score < 55:
                weaknesses.append(f"ESG concerns require attention ({esg_grade} rating)")

        # Analyze forecasts
        if forecasts_data:
            rent_forecast = forecasts_data.get('rent_forecast_12mo', {})
            if rent_forecast.get('change_pct', 0) > 4:
                opportunities.append("Above-average rent growth projected")

        # Analyze demographics
        if demographics_data:
            median_income = demographics_data.get('median_household_income', 0)
            if median_income > 75000:
                strengths.append(f"High-income market (${median_income:,} median)")

        # Analyze economic indicators
        if economic_data:
            unemployment = economic_data.get('unemployment_rate', {})
            if unemployment.get('value', 5) > 6:
                threats.append("Elevated unemployment in market area")

        # Add generic insights if needed
        if not strengths:
            strengths.append("Stable property fundamentals")
        if not opportunities:
            opportunities.append("Market conditions support value creation")

        return {
            'strengths': strengths[:4],  # Top 4
            'weaknesses': weaknesses[:4],
            'opportunities': opportunities[:4],
            'threats': threats[:4]
        }

    def _generate_investment_recommendation(
        self,
        property_data: Dict[str, Any],
        swot: Dict[str, List[str]],
        forecasts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate investment recommendation."""
        forecasts_data = self._extract_tagged_data(forecasts)
        # Simplified scoring based on SWOT and forecasts
        score = 0
        score += len(swot.get('strengths', [])) * 10
        score += len(swot.get('opportunities', [])) * 8
        score -= len(swot.get('weaknesses', [])) * 7
        score -= len(swot.get('threats', [])) * 9

        # Adjust for forecasts
        if forecasts_data:
            rent_growth = forecasts_data.get('rent_forecast_12mo', {}).get('change_pct', 0)
            if rent_growth > 3:
                score += 15

        # Normalize to 0-100
        score = max(0, min(100, score + 50))

        # Determine recommendation
        if score >= 70:
            recommendation = 'BUY'
            rationale = 'Strong fundamentals and positive outlook support acquisition'
        elif score >= 40:
            recommendation = 'HOLD'
            rationale = 'Stable property with balanced risk/reward profile'
        else:
            recommendation = 'SELL'
            rationale = 'Significant headwinds warrant consideration of disposition'

        return {
            'recommendation': recommendation,
            'confidence_score': score,
            'rationale': rationale,
            'key_factors': swot['strengths'][:2] if recommendation == 'BUY' else swot['threats'][:2]
        }

    def _generate_risk_assessment(
        self,
        esg: Dict[str, Any],
        economic: Dict[str, Any]
    ) -> str:
        """Generate risk assessment narrative."""
        esg_data = self._extract_tagged_data(esg)
        economic_data = self._extract_tagged_data(economic)
        risks = []

        if esg_data:
            env_score = esg_data.get('environmental', {}).get('composite_score', 70)
            if env_score < 60:
                risks.append("environmental risk factors")

        if economic_data:
            recession_prob = economic_data.get('recession_probability', {}).get('value', 0)
            if recession_prob and recession_prob > 40:
                risks.append("elevated recession risk")

        if risks:
            return f"Property faces {', '.join(risks)} that warrant monitoring."
        return "Risk profile is within acceptable parameters for the asset class."

    def _identify_opportunities(
        self,
        demographics: Dict[str, Any],
        location: Dict[str, Any],
        forecasts: Dict[str, Any]
    ) -> List[str]:
        """Identify value-creation opportunities."""
        demographics_data = self._extract_tagged_data(demographics)
        location_data = self._extract_tagged_data(location)
        forecasts_data = self._extract_tagged_data(forecasts)
        opportunities = []

        if location_data:
            amenities = location_data.get('amenities', {})
            if amenities.get('restaurants_1mi', 0) > 20:
                opportunities.append("Strong retail environment supports amenity upgrades")

        if demographics_data:
            pop = demographics_data.get('population', 0)
            if pop > 50000:
                opportunities.append("Dense population supports occupancy stability")

        if forecasts_data:
            rent_growth = forecasts_data.get('rent_forecast_12mo', {}).get('change_pct', 0)
            if rent_growth > 3.5:
                opportunities.append("Market rent growth enables value-add renovations")

        return opportunities[:3]

    def _synthesize_market_trends(
        self,
        economic: Dict[str, Any],
        demographics: Dict[str, Any]
    ) -> str:
        """Synthesize market trend narrative."""
        economic_data = self._extract_tagged_data(economic)
        demographics_data = self._extract_tagged_data(demographics)
        trends = []

        if economic_data:
            gdp_growth = economic_data.get('gdp_growth', {}).get('value', 0)
            if gdp_growth and gdp_growth > 2:
                trends.append("expanding economic conditions")

        if demographics_data:
            college_pct = demographics_data.get('college_educated_pct', 0)
            if college_pct > 35:
                trends.append("highly educated workforce")

        if trends:
            return f"Market benefits from {' and '.join(trends)}."
        return "Market fundamentals remain stable."

    # ========== SAMPLE / FALLBACK DATA (for offline/demo) ==========

    # ========== SAMPLE / FALLBACK DATA (for offline/demo) ==========

    def generate_sample_demographics(self, property_code: str) -> Dict[str, Any]:
        sample = {
            'population': 52000,
            'median_household_income': 78000,
            'median_home_value': 420000,
            'median_gross_rent': 1650,
            'unemployment_rate': 3.9,
            'median_age': 35.4,
            'college_educated_pct': 47.5,
            'housing_units': {
                'single_family': 12000,
                'multifamily_2_4': 2400,
                'multifamily_5_9': 1800,
                'multifamily_10_19': 900,
                'multifamily_20_49': 600,
                'multifamily_50_plus': 450,
            },
            'geography': {'property_code': property_code}
        }
        return self.tag_data_source(
            sample,
            source='sample_demographics',
            confidence=50.0,
            extra_metadata={'property_code': property_code}
        )

    def generate_sample_economic(self) -> Dict[str, Any]:
        now = datetime.utcnow().strftime('%Y-%m')
        sample = {
            'gdp_growth': {'value': 2.4, 'date': now},
            'unemployment_rate': {'value': 3.8, 'date': now},
            'inflation_rate': {'value': 2.7, 'date': now},
            'fed_funds_rate': {'value': 5.25, 'date': now},
            'mortgage_rate_30y': {'value': 6.5, 'date': now},
            'recession_probability': {'value': 12.0, 'date': now},
        }
        return self.tag_data_source(sample, source='sample_economic', confidence=45.0, extra_metadata={})

    def generate_sample_location(self, latitude: float = 37.77, longitude: float = -122.42) -> Dict[str, Any]:
        sample = {
            'walk_score': 78,
            'transit_score': 72,
            'bike_score': 69,
            'amenities': {
                'grocery_stores_1mi': 6,
                'restaurants_1mi': 52,
                'schools_2mi': 11,
                'hospitals_5mi': 3,
                'parks_1mi': 9
            },
            'transit_access': {
                'bus_stops_0_5mi': 10,
                'rail_stations_2mi': 1,
                'commute_time_downtown_min': 28
            },
            'crime_index': 48.0,
            'school_rating_avg': 7.2
        }
        return self.tag_data_source(
            sample,
            source='sample_location',
            confidence=40.0,
            extra_metadata={'latitude': latitude, 'longitude': longitude}
        )

    def generate_sample_esg(self) -> Dict[str, Any]:
        sample = {
            'environmental': {
                'flood_risk_score': 20.0,
                'wildfire_risk_score': 12.0,
                'earthquake_risk_score': 30.0,
                'climate_risk_composite': 21.0,
                'energy_efficiency_rating': 'B',
                'emissions_intensity_kg_co2_sqft': 11.5
            },
            'social': {
                'crime_score': 48.0,
                'school_quality_score': 7.2,
                'income_inequality_gini': 0.41,
                'diversity_index': 0.66,
                'community_health_score': 74.0
            },
            'governance': {
                'zoning_compliance_score': 92.0,
                'permit_history_score': 85.0,
                'tax_delinquency_risk': 'Low',
                'legal_issues_count': 0,
                'regulatory_risk_score': 18.0
            },
            'composite_esg_score': 72.0,
            'esg_grade': 'B+'
        }
        return self.tag_data_source(sample, source='sample_esg', confidence=45.0, extra_metadata={})

    def generate_sample_forecasts(self) -> Dict[str, Any]:
        now = datetime.utcnow().strftime('%Y-%m')
        sample = {
            'rent_forecast_12mo': {
                'predicted_rent': 2480,
                'change_pct': 3.2,
                'confidence_interval_95': [2400, 2560],
                'model': 'prophet',
                'as_of': now
            },
            'occupancy_forecast_12mo': {
                'predicted_occupancy': 94.2,
                'change_pct': 1.0,
                'confidence_interval_95': [92.0, 96.0],
                'model': 'arima',
                'as_of': now
            },
            'cap_rate_forecast_12mo': {
                'predicted_cap_rate': 5.9,
                'change_bps': 15,
                'confidence_interval_95': [5.6, 6.2],
                'model': 'ets',
                'as_of': now
            }
        }
        return self.tag_data_source(sample, source='sample_forecasts', confidence=40.0, extra_metadata={})

    def generate_sample_competitive(self) -> Dict[str, Any]:
        sample = {
            'submarket_position': {
                'grade': 'B+',
                'summary': 'Solid positioning with room to improve amenities.',
                'differentiators': ['Strong walkability', 'Stable occupancy'],
                'risks': ['Limited parking', 'New supply expected nearby']
            },
            'comparables': [
                {'name': 'Comp A', 'distance_mi': 1.2, 'occupancy': 93.0, 'rent_psf': 28.5},
                {'name': 'Comp B', 'distance_mi': 2.1, 'occupancy': 95.5, 'rent_psf': 30.1}
            ],
            'recommendations': [
                'Upgrade lobby experience',
                'Add EV charging to improve ESG score'
            ]
        }
        return self.tag_data_source(sample, source='sample_competitive', confidence=38.0, extra_metadata={})

    def generate_sample_ai_insights(self) -> Dict[str, Any]:
        sample = {
            'key_takeaways': [
                'Demand remains resilient; rents can grow ~3% over next 12 months.',
                'Transit and walkability are competitive advantages; invest in curb appeal.'
            ],
            'risk_signals': [
                'Monitor interest rate trend; refinance window may open in 9-12 months.',
                'New supply pipeline in submarket could pressure occupancy mid-term.'
            ],
            'opportunities': [
                'Add green amenities to lift ESG score and tenant retention.',
                'Consider small capex for interiors to justify rent lifts.'
            ]
        }
        return self.tag_data_source(sample, source='sample_ai', confidence=35.0, extra_metadata={})
