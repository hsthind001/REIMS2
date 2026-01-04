/**
 * Demographics Panel Component
 *
 * Displays Census demographics data with visualizations
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  People as PeopleIcon,
  AttachMoney as MoneyIcon,
  Home as HomeIcon,
  School as SchoolIcon,
  WorkOff as WorkOffIcon,
} from '@mui/icons-material';
import type { Demographics } from '../../types/market-intelligence';
import * as marketIntelligenceService from '../../services/marketIntelligenceService';

interface DemographicsPanelProps {
  data: Demographics;
  propertyCode: string;
  onRefresh?: () => void;
}

interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color = 'primary' }) => {
  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2}>
          <Box
            sx={{
              backgroundColor: `${color}.main`,
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
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h5" fontWeight="bold">
              {value}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

const DemographicsPanel: React.FC<DemographicsPanelProps> = ({ data, propertyCode, onRefresh }) => {
  const { data: demographics, lineage } = data;

  const confidenceColor = marketIntelligenceService.getConfidenceBadgeColor(lineage.confidence);

  return (
    <Box p={3}>
      {/* Data Source Info */}
      <Box mb={3} display="flex" gap={1} flexWrap="wrap" alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Data Source:
        </Typography>
        <Chip label={lineage.source.toUpperCase()} size="small" />
        <Chip label={`Vintage: ${marketIntelligenceService.formatVintage(lineage.vintage)}`} size="small" />
        <Chip
          label={`Confidence: ${lineage.confidence}%`}
          size="small"
          color={confidenceColor}
        />
        <Chip
          label={`Fetched: ${new Date(lineage.fetched_at).toLocaleString()}`}
          size="small"
          variant="outlined"
        />
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Key Metrics */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Key Metrics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Population"
            value={marketIntelligenceService.formatNumber(demographics.population)}
            icon={<PeopleIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Median Household Income"
            value={marketIntelligenceService.formatCurrency(demographics.median_household_income)}
            icon={<MoneyIcon />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Median Home Value"
            value={marketIntelligenceService.formatCurrency(demographics.median_home_value)}
            icon={<HomeIcon />}
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Median Gross Rent"
            value={marketIntelligenceService.formatCurrency(demographics.median_gross_rent)}
            icon={<HomeIcon />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="College Educated"
            value={marketIntelligenceService.formatPercentage(demographics.college_educated_pct)}
            icon={<SchoolIcon />}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Unemployment Rate"
            value={marketIntelligenceService.formatPercentage(demographics.unemployment_rate)}
            icon={<WorkOffIcon />}
            color="error"
          />
        </Grid>
      </Grid>

      {/* Additional Demographics */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Additional Demographics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                General Information
              </Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>Median Age</TableCell>
                    <TableCell align="right">
                      {demographics.median_age ? `${demographics.median_age} years` : 'N/A'}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                Geography
              </Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>State FIPS</TableCell>
                    <TableCell align="right">{demographics.geography.state_fips}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>County FIPS</TableCell>
                    <TableCell align="right">{demographics.geography.county_fips}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Census Tract</TableCell>
                    <TableCell align="right">{demographics.geography.tract}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Housing Units Breakdown */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Housing Units by Type
      </Typography>
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Housing Type</TableCell>
              <TableCell align="right">Units</TableCell>
              <TableCell align="right">Percentage</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(() => {
              const totalUnits =
                demographics.housing_units.single_family +
                demographics.housing_units.multifamily_2_4 +
                demographics.housing_units.multifamily_5_9 +
                demographics.housing_units.multifamily_10_19 +
                demographics.housing_units.multifamily_20_49 +
                demographics.housing_units.multifamily_50_plus;

              const rows = [
                { label: 'Single Family', value: demographics.housing_units.single_family },
                { label: 'Multifamily (2-4 units)', value: demographics.housing_units.multifamily_2_4 },
                { label: 'Multifamily (5-9 units)', value: demographics.housing_units.multifamily_5_9 },
                { label: 'Multifamily (10-19 units)', value: demographics.housing_units.multifamily_10_19 },
                { label: 'Multifamily (20-49 units)', value: demographics.housing_units.multifamily_20_49 },
                { label: 'Multifamily (50+ units)', value: demographics.housing_units.multifamily_50_plus },
              ];

              return (
                <>
                  {rows.map((row) => (
                    <TableRow key={row.label}>
                      <TableCell>{row.label}</TableCell>
                      <TableCell align="right">
                        {marketIntelligenceService.formatNumber(row.value)}
                      </TableCell>
                      <TableCell align="right">
                        {totalUnits > 0
                          ? marketIntelligenceService.formatPercentage((row.value / totalUnits) * 100, 1)
                          : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow sx={{ backgroundColor: 'action.hover' }}>
                    <TableCell>
                      <strong>Total</strong>
                    </TableCell>
                    <TableCell align="right">
                      <strong>{marketIntelligenceService.formatNumber(totalUnits)}</strong>
                    </TableCell>
                    <TableCell align="right">
                      <strong>100.0%</strong>
                    </TableCell>
                  </TableRow>
                </>
              );
            })()}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DemographicsPanel;
