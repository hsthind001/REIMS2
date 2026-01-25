/**
 * Competitive Analysis Panel
 *
 * Displays submarket positioning, competitive threats, and market trends
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  List,
  ListItem,
  ListItemText,
  Grid,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingFlat as TrendingFlatIcon,
  TrendingDown as TrendingDownIcon,
  LocationOn as LocationIcon,
  Star as StarIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
  HelpOutline as UnknownIcon,
} from '@mui/icons-material';
import type { CompetitiveAnalysis } from '../../types/market-intelligence';

interface CompetitiveAnalysisPanelProps {
  data: CompetitiveAnalysis;
  propertyCode: string;
  onRefresh?: () => void;
}

interface PercentileCardProps {
  title: string;
  percentile: number | null;
  icon: React.ReactNode;
  color: string;
}

const PercentileCard: React.FC<PercentileCardProps> = ({ title, percentile, icon, color }) => {
  const getPercentileLabel = (pct: number | null): string => {
    if (pct === null) return 'Data Unavailable';
    if (pct >= 75) return 'Top Quartile';
    if (pct >= 50) return 'Above Average';
    if (pct >= 25) return 'Below Average';
    return 'Bottom Quartile';
  };

  const getPercentileColor = (pct: number | null): string => {
    if (pct === null) return '#9e9e9e';
    if (pct >= 75) return '#2e7d32';
    if (pct >= 50) return '#66bb6a';
    if (pct >= 25) return '#ffa726';
    return '#f44336';
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Box
            sx={{
              backgroundColor: percentile !== null ? color : '#e0e0e0',
              color: percentile !== null ? 'white' : '#757575',
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
            <Typography variant="h4" fontWeight="bold" color={percentile === null ? 'text.secondary' : 'text.primary'}>
              {percentile !== null ? percentile.toFixed(0) : 'N/A'}
              {percentile !== null && (
                <Typography component="span" variant="h6" color="text.secondary">
                  th
                </Typography>
              )}
            </Typography>
            <Chip
              label={getPercentileLabel(percentile)}
              size="small"
              sx={{
                backgroundColor: getPercentileColor(percentile),
                color: 'white',
                mt: 0.5,
              }}
            />
          </Box>
        </Box>
        <LinearProgress
          variant="determinate"
          value={percentile || 0}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: '#e0e0e0',
            '& .MuiLinearProgress-bar': {
              backgroundColor: getPercentileColor(percentile),
            },
            opacity: percentile === null ? 0.3 : 1
          }}
        />
        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          Percentile ranking within submarket
        </Typography>
      </CardContent>
    </Card>
  );
};

const CompetitiveAnalysisPanel: React.FC<CompetitiveAnalysisPanelProps> = ({ data }) => {
  const competitive = data.data;
  const position = competitive.submarket_position;
  const threats = competitive.competitive_threats;
  const trends = competitive.submarket_trends;

  const getThreatSeverity = (score: number): 'error' | 'warning' | 'success' => {
    if (score >= 70) return 'error';
    if (score >= 40) return 'warning';
    return 'success';
  };

  const getTrendIcon = (trend: string | null) => {
    if (!trend) return <UnknownIcon color="disabled" />;
    
    if (trend.toLowerCase().includes('increasing') || trend.toLowerCase().includes('rising')) {
      return <TrendingUpIcon color="success" />;
    }
    if (trend.toLowerCase().includes('decreasing') || trend.toLowerCase().includes('falling')) {
      return <TrendingDownIcon color="error" />;
    }
    return <TrendingFlatIcon color="action" />;
  };

  return (
    <Box p={3}>
      {/* Submarket Position */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Submarket Position
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Property ranking within the competitive submarket across key metrics
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <PercentileCard
            title="Rent Level"
            percentile={position.rent_percentile}
            icon={<TrendingUpIcon />}
            color="#1976d2"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <PercentileCard
            title="Occupancy"
            percentile={position.occupancy_percentile}
            icon={<CheckIcon />}
            color="#9c27b0"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <PercentileCard
            title="Quality"
            percentile={position.quality_percentile}
            icon={<StarIcon />}
            color="#ff9800"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <PercentileCard
            title="Value"
            percentile={position.value_percentile}
            icon={<LocationIcon />}
            color="#00796b"
          />
        </Grid>
      </Grid>

      {/* Competitive Threats */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Competitive Threats
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Nearby properties that pose competitive risks
      </Typography>

      <Grid container spacing={3} mb={4}>
        {threats.length > 0 ? (
          threats.map((threat, index) => (
            <Grid size={{ xs: 12, md: 6 }} key={index}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" fontWeight="bold">
                      {threat.property_name}
                    </Typography>
                    <Chip
                      label={`Threat: ${threat.threat_score}/100`}
                      color={getThreatSeverity(threat.threat_score)}
                      size="small"
                    />
                  </Box>

                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <LocationIcon fontSize="small" color="action" />
                    <Typography variant="body2" color="text.secondary">
                      {threat.distance_mi.toFixed(1)} miles away
                    </Typography>
                  </Box>

                  <Box mb={2}>
                    <Typography variant="subtitle2" color="error.main" gutterBottom>
                      Their Advantages:
                    </Typography>
                    <List dense disablePadding>
                      {threat.advantages.length > 0 ? (
                        threat.advantages.map((adv, idx) => (
                          <ListItem key={idx} disablePadding>
                            <WarningIcon sx={{ fontSize: 16, mr: 1, color: 'error.main' }} />
                            <ListItemText primary={adv} primaryTypographyProps={{ variant: 'body2' }} />
                          </ListItem>
                        ))
                      ) : (
                        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          No data available
                        </Typography>
                      )}
                    </List>
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" color="success.main" gutterBottom>
                      Our Advantages:
                    </Typography>
                    <List dense disablePadding>
                      {threat.disadvantages.length > 0 ? (
                        threat.disadvantages.map((dis, idx) => (
                          <ListItem key={idx} disablePadding>
                            <CheckIcon sx={{ fontSize: 16, mr: 1, color: 'success.main' }} />
                            <ListItemText primary={dis} primaryTypographyProps={{ variant: 'body2' }} />
                          </ListItem>
                        ))
                      ) : (
                         <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          No data available
                        </Typography>
                      )}
                    </List>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))
        ) : (
          <Grid size={{ xs: 12 }}>
            <Alert severity="info" variant="outlined">
              No specific competitive threats identified in the immediate vicinity (within 5 miles).
            </Alert>
          </Grid>
        )}
      </Grid>

      {/* Submarket Trends */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Submarket Trends
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Market dynamics and supply/demand indicators
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              {getTrendIcon(trends.occupancy_trend)}
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Occupancy Trend
                </Typography>
                <Typography variant="h5" fontWeight="bold" textTransform="capitalize">
                  {trends.occupancy_trend || 'Unknown'}
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Rent Growth (3-Year CAGR)
            </Typography>
            <Typography variant="h4" fontWeight="bold" color={trends.rent_growth_3yr_cagr !== null ? "primary" : "text.secondary"}>
              {trends.rent_growth_3yr_cagr !== null ? `${trends.rent_growth_3yr_cagr.toFixed(1)}%` : 'N/A'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Compound annual growth rate
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Supply & Demand Table */}
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Supply/Demand Metric</strong>
              </TableCell>
              <TableCell align="right">
                <strong>Value</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>New Supply Pipeline</TableCell>
              <TableCell align="right">
                {trends.new_supply_pipeline_units !== null ? (
                  <Chip label={`${trends.new_supply_pipeline_units} units`} color="warning" size="small" />
                ) : (
                  <Typography variant="body2" color="text.secondary">N/A</Typography>
                )}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Absorption Rate</TableCell>
              <TableCell align="right">
                {trends.absorption_rate_units_per_mo !== null ? (
                  <Chip label={`${trends.absorption_rate_units_per_mo} units/month`} color="info" size="small" />
                ) : (
                   <Typography variant="body2" color="text.secondary">N/A</Typography>
                )}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Months of Supply</TableCell>
              <TableCell align="right">
                {trends.months_of_supply !== null ? (
                  <Chip
                    label={`${trends.months_of_supply.toFixed(1)} months`}
                    color={trends.months_of_supply > 6 ? 'error' : 'success'}
                    size="small"
                  />
                ) : (
                   <Typography variant="body2" color="text.secondary">N/A</Typography>
                )}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>

      {/* Interpretation */}
      <Alert severity="info" icon={<InfoIcon />}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          Competitive Analysis Interpretation
        </Typography>
        <Typography variant="caption">
          {position.rent_percentile !== null ? (
            position.rent_percentile >= 50
              ? 'The property is positioned in the upper half of the market for rent pricing. '
              : 'The property is positioned in the lower half of the market for rent pricing. '
          ) : 'Insufficient data to determine market rent positioning. '}
          
          {threats.length > 0
            ? `There are ${threats.length} competitive threats within the immediate area. `
            : 'No significant competitive threats identified in the immediate area. '}
          
          {trends.months_of_supply !== null ? (
            trends.months_of_supply > 6
              ? 'The high months of supply indicates potential oversupply in the submarket.'
              : 'The market shows healthy supply/demand balance based on absorption.'
          ) : 'Supply and demand metrics are currently unavailable for this submarket.'}
        </Typography>
      </Alert>

      {/* Data Source */}
      <Box mt={3}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Data Source
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.source}
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Analysis Date
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.vintage}
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Confidence
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.confidence}%
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Threats Identified
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {threats.length}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default CompetitiveAnalysisPanel;
