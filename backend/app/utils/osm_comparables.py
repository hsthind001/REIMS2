"""
OpenStreetMap Comparables Service

Uses Nominatim (geocoding) and Overpass API (nearby buildings) to find
real comparable commercial properties. Free and open source.

APIs:
- Nominatim: https://nominatim.openstreetmap.org/ (geocoding)
- Overpass API: https://overpass-api.de/api/ (nearby buildings)
"""
import httpx
import logging
from typing import List, Dict, Optional, Tuple
from math import radians, cos, sin, asin, sqrt

logger = logging.getLogger(__name__)


class OSMComparablesService:
    """
    Find comparable commercial properties using OpenStreetMap
    
    Free, open source, no API key required
    Rate limits: 1 request/second (Nominatim), reasonable use (Overpass)
    """
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.client = httpx.Client(timeout=30.0, headers={
            'User-Agent': 'REIMS2/1.0 (Real Estate Investment Management System)'  # Required by Nominatim
        })
    
    def find_comparables(
        self,
        property_address: str,
        city: str,
        state: str,
        zip_code: Optional[str] = None,
        radius_miles: float = 2.0,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Find comparable commercial properties near the given address
        
        Args:
            property_address: Street address
            city: City name
            state: State code (e.g., "CA", "NY")
            zip_code: Optional ZIP code
            radius_miles: Search radius in miles (default: 2.0)
            max_results: Maximum number of comparables to return
        
        Returns:
            List of comparable property dicts with:
            - name: Property name or address
            - distance: Distance in miles
            - capRate: Estimated cap rate (uses portfolio average)
            - occupancy: Estimated occupancy (uses portfolio average)
            - address: Full address if available
        """
        try:
            # Step 1: Geocode the property address to get coordinates
            lat, lon = self._geocode_address(property_address, city, state, zip_code)
            if not lat or not lon:
                logger.warning(f"Could not geocode address: {property_address}, {city}, {state}")
                return []
            
            # Step 2: Find nearby commercial buildings using Overpass API
            logger.info(f"Searching for commercial buildings within {radius_miles} miles of ({lat}, {lon})")
            nearby_buildings = self._find_nearby_buildings(lat, lon, radius_miles, max_results)
            
            if not nearby_buildings:
                logger.warning(f"No nearby commercial buildings found for {property_address or city}")
                return []
            
            logger.info(f"Found {len(nearby_buildings)} nearby buildings")
            
            # Step 3: Calculate distances and format results
            comparables = []
            for building in nearby_buildings:
                building_lat = building.get('lat')
                building_lon = building.get('lon')
                if building_lat and building_lon:
                    distance_miles = self._calculate_distance(lat, lon, building_lat, building_lon)
                    
                    # Get building name or use address
                    name = building.get('name') or building.get('addr:street', 'Commercial Property')
                    if building.get('addr:housenumber'):
                        name = f"{building.get('addr:housenumber')} {name}"
                    
                    comparables.append({
                        "name": name,
                        "distance": round(distance_miles, 2),
                        "address": self._format_address(building),
                        "lat": building_lat,
                        "lon": building_lon
                    })
            
            # Sort by distance
            comparables.sort(key=lambda x: x['distance'])
            
            return comparables[:max_results]
            
        except Exception as e:
            logger.error(f"Error finding comparables: {str(e)}")
            return []
    
    def _geocode_address(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: Optional[str] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocode address to latitude/longitude using Nominatim
        
        Returns: (latitude, longitude) or (None, None) if failed
        """
        try:
            # Build query string - work with what we have
            query_parts = []
            if address and address.strip():
                query_parts.append(address.strip())
            if city and city.strip():
                query_parts.append(city.strip())
            if state and state.strip():
                query_parts.append(state.strip())
            if zip_code and zip_code.strip():
                query_parts.append(zip_code.strip())
            
            if not query_parts:
                logger.warning("No address components provided for geocoding")
                return None, None
            
            query = ", ".join(query_parts)
            logger.info(f"Attempting to geocode: {query}")
            
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }
            
            # Rate limit: 1 request per second
            import time
            time.sleep(1.1)  # Be respectful to Nominatim
            
            response = self.client.get(self.nominatim_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                lat = float(result.get('lat', 0))
                lon = float(result.get('lon', 0))
                if lat != 0 and lon != 0:
                    logger.info(f"Successfully geocoded '{query}' to ({lat}, {lon})")
                    return lat, lon
                else:
                    logger.warning(f"Geocoding returned invalid coordinates for '{query}'")
            
            logger.warning(f"No geocoding results found for '{query}'")
            return None, None
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Geocoding HTTP error: {e.response.status_code} - {e.response.text}")
            return None, None
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}", exc_info=True)
            return None, None
    
    def _find_nearby_buildings(
        self,
        lat: float,
        lon: float,
        radius_miles: float,
        max_results: int
    ) -> List[Dict]:
        """
        Find nearby commercial buildings using Overpass API
        
        Searches for:
        - Commercial buildings (shop, retail, office)
        - Buildings with names or addresses
        - Within specified radius
        """
        try:
            # Convert miles to meters (Overpass uses meters)
            radius_meters = radius_miles * 1609.34
            
            # Overpass QL query to find commercial buildings
            # More inclusive query to find various commercial properties
            query = f"""
            [out:json][timeout:25];
            (
              // Named commercial buildings
              way["building"]["name"](around:{radius_meters},{lat},{lon});
              // Commercial building types
              way["building"="commercial"](around:{radius_meters},{lat},{lon});
              way["building"="retail"](around:{radius_meters},{lat},{lon});
              way["building"="office"](around:{radius_meters},{lat},{lon});
              way["building"="shop"](around:{radius_meters},{lat},{lon});
              way["building"="warehouse"](around:{radius_meters},{lat},{lon});
              // Buildings with commercial amenities
              way["amenity"="marketplace"](around:{radius_meters},{lat},{lon});
              way["amenity"="restaurant"](around:{radius_meters},{lat},{lon});
              way["amenity"="bank"](around:{radius_meters},{lat},{lon});
              // Shops and retail
              way["shop"](around:{radius_meters},{lat},{lon});
              way["office"](around:{radius_meters},{lat},{lon});
            );
            out center meta;
            """
            
            response = self.client.post(
                self.overpass_url,
                content=query,
                headers={'Content-Type': 'text/plain'}
            )
            response.raise_for_status()
            
            data = response.json()
            buildings = []
            
            if 'elements' in data:
                for element in data['elements']:
                    if element.get('type') == 'way':
                        # Get center coordinates
                        center = element.get('center', {})
                        building_lat = center.get('lat')
                        building_lon = center.get('lon')
                        
                        if building_lat and building_lon:
                            # Extract building info
                            tags = element.get('tags', {})
                            building_info = {
                                'lat': building_lat,
                                'lon': building_lon,
                                'name': tags.get('name'),
                                'addr:housenumber': tags.get('addr:housenumber'),
                                'addr:street': tags.get('addr:street'),
                                'addr:city': tags.get('addr:city'),
                                'addr:state': tags.get('addr:state'),
                                'addr:postcode': tags.get('addr:postcode'),
                                'building': tags.get('building'),
                                'shop': tags.get('shop'),
                                'office': tags.get('office')
                            }
                            buildings.append(building_info)
            
            logger.info(f"Found {len(buildings)} nearby buildings from Overpass API")
            return buildings
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Overpass API HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Overpass API error: {str(e)}", exc_info=True)
            return []
    
    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Returns distance in miles
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in miles
        r = 3956
        
        return c * r
    
    def _format_address(self, building: Dict) -> str:
        """Format building address from OSM tags"""
        parts = []
        if building.get('addr:housenumber'):
            parts.append(building['addr:housenumber'])
        if building.get('addr:street'):
            parts.append(building['addr:street'])
        if building.get('addr:city'):
            parts.append(building['addr:city'])
        if building.get('addr:state'):
            parts.append(building['addr:state'])
        if building.get('addr:postcode'):
            parts.append(building['addr:postcode'])
        
        return ", ".join(parts) if parts else "Address not available"
    
    def close(self):
        """Close HTTP client"""
        self.client.close()

