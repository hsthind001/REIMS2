/**
 * Location Intelligence Panel
 *
 * Displays location intelligence data including walkability scores,
 * amenity counts, transit access, and neighborhood characteristics
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  Tooltip,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  DirectionsWalk as WalkIcon,
  DirectionsBus as TransitIcon,
  DirectionsBike as BikeIcon,
  LocalGroceryStore as GroceryIcon,
  Restaurant as RestaurantIcon,
  School as SchoolIcon,
  LocalHospital as HospitalIcon,
  Park as ParkIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import type { LocationIntelligence } from '../../types/market-intelligence';

interface LocationIntelligencePanelProps {
  data: LocationIntelligence;
  propertyCode: string;
  onRefresh?: () => void;
}

interface ScoreCardProps {
  title: string;
  score: number;
  icon: React.ReactNode;
  description: string;
  color: string;
}

const ScoreCard: React.FC<ScoreCardProps> = ({ title, score, icon, description, color }) => {
  const getScoreLabel = (score: number): string => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Very Good';
    if (score >= 50) return 'Good';
    if (score >= 25) return 'Fair';
    return 'Limited';
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return '#2e7d32'; // Dark green
    if (score >= 70) return '#66bb6a'; // Green
    if (score >= 50) return '#ffa726'; // Orange
    if (score >= 25) return '#ff9800'; // Dark orange
    return '#f44336'; // Red
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Box
            sx={{
              backgroundColor: color,
              color: 'white',
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </Box>
          <Box flex={1}>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h4" fontWeight="bold">
              {score}
            </Typography>
            <Chip
              label={getScoreLabel(score)}
              size="small"
              sx={{
                backgroundColor: getScoreColor(score),
                color: 'white',
                mt: 0.5,
              }}
            />
          </Box>
        </Box>
        <LinearProgress
          variant="determinate"
          value={score}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: '#e0e0e0',
            '& .MuiLinearProgress-bar': {
              backgroundColor: getScoreColor(score),
            },
          }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
};

const LocationIntelligencePanel: React.FC<LocationIntelligencePanelProps> = ({
  data,
  propertyCode,
  onRefresh,
}) => {
  const { data: loc, lineage } = data;
  const amenityIcons: Record<string, React.ReactNode> = {
    grocery_stores_1mi: <GroceryIcon />,
    restaurants_1mi: <RestaurantIcon />,
    schools_2mi: <SchoolIcon />,
    hospitals_5mi: <HospitalIcon />,
    parks_1mi: <ParkIcon />,
  };

  const amenityLabels: Record<string, string> = {
    grocery_stores_1mi: 'Grocery Stores (1 mi)',
    restaurants_1mi: 'Restaurants (1 mi)',
    schools_2mi: 'Schools (2 mi)',
    hospitals_5mi: 'Hospitals (5 mi)',
    parks_1mi: 'Parks (1 mi)',
  };

  const transitLabels: Record<string, string> = {
    bus_stops_0_5mi: 'Bus Stops (0.5 mi)',
    subway_stations_1mi: 'Subway/Rail Stations (1 mi)',
    rail_stations_2mi: 'Rail Stations (2 mi)',
    commute_time_downtown_min: 'Est. Commute to Downtown (min)',
  };

  const confidenceColor =
    lineage && lineage.confidence !== undefined
      ? lineage.confidence >= 85
        ? 'success'
        : lineage.confidence >= 60
        ? 'warning'
        : 'default'
      : 'default';

  return (
    <Box p={3}>
      {lineage && (
        <Box mb={3} display="flex" gap={1} flexWrap="wrap" alignItems="center">
          <Typography variant="body2" color="text.secondary">
            Data Source:
          </Typography>
          <Chip label={(lineage.source || 'unknown').toUpperCase()} size="small" />
          {lineage.vintage && <Chip label={`Vintage: ${lineage.vintage}`} size="small" />}
          {lineage.confidence !== undefined && (
            <Chip label={`Confidence: ${lineage.confidence}%`} size="small" color={confidenceColor} />
          )}
          {lineage.fetched_at && (
            <Chip
              label={`Fetched: ${new Date(lineage.fetched_at).toLocaleString()}`}
              size="small"
              variant="outlined"
            />
          )}
        </Box>
      )}
      {/* Walkability Scores */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Walkability & Accessibility
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Location scores based on proximity to amenities, transit access, and neighborhood walkability
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Walk Score"
            score={loc.walk_score}
            icon={<WalkIcon />}
            description="Walkability based on nearby amenities and pedestrian infrastructure"
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Transit Score"
            score={loc.transit_score}
            icon={<TransitIcon />}
            description="Public transportation access and frequency of service"
            color="#9c27b0"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Bike Score"
            score={loc.bike_score}
            icon={<BikeIcon />}
            description="Bikeability based on bike lanes, trails, and infrastructure"
            color="#ff9800"
          />
        </Grid>
      </Grid>

      {/* Amenities */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Nearby Amenities
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Count of key amenities within walking and driving distance
      </Typography>

      <Grid container spacing={3} mb={4}>
        {Object.entries(loc.amenities).map(([key, count]) => (
          <Grid item xs={12} sm={6} md={4} key={key}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box
                    sx={{
                      backgroundColor: '#00796b',
                      color: 'white',
                      p: 1.5,
                      borderRadius: 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {amenityIcons[key] || <InfoIcon />}
                  </Box>
                  <Box flex={1}>
                    <Typography variant="body2" color="text.secondary">
                      {amenityLabels[key] || key}
                    </Typography>
                    <Typography variant="h4" fontWeight="bold">
                      {count}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Map */}
      {lineage?.extra_metadata?.latitude && lineage?.extra_metadata?.longitude && (
        <Box mb={4} height={360} sx={{ borderRadius: 2, overflow: 'hidden', border: '1px solid #e0e0e0' }}>
          <MapContainer
            center={[lineage.extra_metadata.latitude, lineage.extra_metadata.longitude]}
            zoom={14}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker
              position={[lineage.extra_metadata.latitude, lineage.extra_metadata.longitude]}
              icon={L.icon({
                iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
                iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
                shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
              })}
            >
              <Popup>Property</Popup>
            </Marker>
            {Array.isArray(loc.isochrones) &&
              loc.isochrones.map((iso: any, idx: number) =>
                iso.geometry ? (
                  <GeoJSON
                    key={idx}
                    data={iso.geometry}
                    style={{ color: '#1976d2', weight: 1, fillOpacity: 0.1 }}
                  />
                ) : null
              )}
          </MapContainer>
        </Box>
      )}

      {/* Transit Access */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Public Transit Access
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Number of public transportation stops and stations near the property
      </Typography>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Transit Type</strong>
              </TableCell>
              <TableCell align="right">
                <strong>Count</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(loc.transit_access).map(([key, count]) => (
              <TableRow key={key}>
                <TableCell>{transitLabels[key] || key}</TableCell>
                <TableCell align="right">
                  <Chip label={count as number} color={(count as number) > 0 ? 'success' : 'default'} size="small" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Crime Index Placeholder */}
      {loc.crime_index !== null && (
        <Box mb={4}>
          <Typography variant="h5" gutterBottom fontWeight="bold">
            Safety & Crime
          </Typography>
          <Alert severity="info" icon={<InfoIcon />}>
            Crime index data: {loc.crime_index} (Lower is better)
            <br />
            <Typography variant="caption" color="text.secondary">
              Crime data integration coming in future update
            </Typography>
          </Alert>
        </Box>
      )}

      {/* School Ratings Placeholder */}
      {loc.school_rating_avg !== null && (
        <Box mb={4}>
          <Typography variant="h5" gutterBottom fontWeight="bold">
            School Ratings
          </Typography>
          <Alert severity="info" icon={<InfoIcon />}>
            Average school rating: {loc.school_rating_avg}/10
            <br />
            <Typography variant="caption" color="text.secondary">
              Detailed school ratings integration coming in future update
            </Typography>
          </Alert>
        </Box>
      )}

      {/* Data Source Information */}
      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          Data Sources
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Provider
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                OpenStreetMap
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                API
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                Overpass API
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Confidence
              </Typography>
              <Tooltip title="Data quality and freshness indicator">
                <Typography variant="body2" fontWeight="bold">
                  85%
                </Typography>
              </Tooltip>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Last Updated
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                Real-time
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default LocationIntelligencePanel;
