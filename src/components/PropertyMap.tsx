import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { Icon } from 'leaflet';
import type { Property } from '../types/api';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icon in react-leaflet
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Set up default icon
const defaultIcon = new Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

interface PropertyLocation extends Property {
  lat: number;
  lng: number;
}

interface PropertyMapProps {
  properties: Property[];
  selectedProperty?: Property | null;
  onPropertySelect?: (property: Property) => void;
  height?: number;
}

// Component to auto-fit map bounds when properties change
function MapBounds({ locations }: { locations: PropertyLocation[] }) {
  const map = useMap();

  useEffect(() => {
    if (locations.length > 0) {
      const bounds = locations.map((loc) => [loc.lat, loc.lng] as [number, number]);
      if (bounds.length === 1) {
        // Single property - center on it
        map.setView(bounds[0], 13);
      } else {
        // Multiple properties - fit all
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [locations, map]);

  return null;
}

// Simple geocoding function for US addresses
// In production, you'd use a real geocoding service (Google Maps, Mapbox, etc.)
async function geocodeAddress(property: Property): Promise<PropertyLocation | null> {
  // For demo purposes, generate approximate coordinates based on state
  // In production, replace with actual geocoding API call
  const stateCoordinates: { [key: string]: { lat: number; lng: number } } = {
    'CA': { lat: 36.7783, lng: -119.4179 },
    'NY': { lat: 40.7128, lng: -74.0060 },
    'TX': { lat: 31.9686, lng: -99.9018 },
    'FL': { lat: 27.9944, lng: -81.7603 },
    'IL': { lat: 40.6331, lng: -89.3985 },
    'PA': { lat: 40.2732, lng: -76.8867 },
    'OH': { lat: 40.4173, lng: -82.9071 },
    'GA': { lat: 32.1656, lng: -82.9001 },
    'NC': { lat: 35.7596, lng: -79.0193 },
    'MI': { lat: 44.3148, lng: -85.6024 },
  };

  const state = property.state?.toUpperCase() || 'CA';
  const baseCoords = stateCoordinates[state] || stateCoordinates['CA'];

  // Add small random offset to show different properties in same state
  // (in production, use real geocoding)
  const latOffset = (Math.random() - 0.5) * 2; // ±1 degree
  const lngOffset = (Math.random() - 0.5) * 2;

  return {
    ...property,
    lat: baseCoords.lat + latOffset,
    lng: baseCoords.lng + lngOffset
  };
}

export const PropertyMap: React.FC<PropertyMapProps> = ({
  properties,
  selectedProperty,
  onPropertySelect,
  height = 500
}) => {
  const [locations, setLocations] = useState<PropertyLocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const geocodeProperties = async () => {
      setLoading(true);
      const locationPromises = properties.map(async (property) => {
        try {
          return await geocodeAddress(property);
        } catch (err) {
          console.error(`Failed to geocode ${property.property_name}:`, err);
          return null;
        }
      });

      const results = await Promise.all(locationPromises);
      const validLocations = results.filter((loc): loc is PropertyLocation => loc !== null);
      setLocations(validLocations);
      setLoading(false);
    };

    if (properties.length > 0) {
      geocodeProperties();
    } else {
      setLocations([]);
      setLoading(false);
    }
  }, [properties]);

  // Default center (United States)
  const defaultCenter: [number, number] = [39.8283, -98.5795];
  const defaultZoom = 4;

  if (loading) {
    return (
      <div
        style={{ height: `${height}px` }}
        className="flex items-center justify-center bg-gray-100 rounded-lg"
      >
        <p className="text-gray-600">Loading map...</p>
      </div>
    );
  }

  if (locations.length === 0) {
    return (
      <div
        style={{ height: `${height}px` }}
        className="flex items-center justify-center bg-gray-100 rounded-lg"
      >
        <p className="text-gray-600">No properties to display on map</p>
      </div>
    );
  }

  return (
    <div style={{ height: `${height}px` }} className="rounded-lg overflow-hidden shadow-lg">
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBounds locations={locations} />

        {locations.map((location) => {
          const isSelected = selectedProperty?.id === location.id;
          return (
            <Marker
              key={location.id}
              position={[location.lat, location.lng]}
              icon={defaultIcon}
              eventHandlers={{
                click: () => onPropertySelect?.(location)
              }}
            >
              <Popup>
                <div className="p-2">
                  <h3 className="font-bold text-lg mb-1">{location.property_name}</h3>
                  <p className="text-sm text-gray-600 mb-1">{location.property_code}</p>
                  {location.address && (
                    <p className="text-sm mb-1">{location.address}</p>
                  )}
                  {location.city && location.state && (
                    <p className="text-sm mb-2">{location.city}, {location.state}</p>
                  )}
                  {location.property_type && (
                    <p className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded inline-block">
                      {location.property_type}
                    </p>
                  )}
                  {isSelected && (
                    <p className="text-xs mt-2 text-green-600 font-semibold">
                      ✓ Currently Selected
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};
