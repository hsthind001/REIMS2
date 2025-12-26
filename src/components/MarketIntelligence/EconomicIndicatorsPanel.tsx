/**
 * Economic Indicators Panel Component
 *
 * Displays FRED economic indicators data with visualizations
 */

import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
  Divider,
  Alert,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  ShowChart as ShowChartIcon,
} from '@mui/icons-material';
import type { EconomicIndicators, EconomicIndicatorValue } from '../../types/market-intelligence';
import * as marketIntelligenceService from '../../services/marketIntelligenceService';

interface EconomicIndicatorsPanelProps {
  data: EconomicIndicators;
  propertyCode: string;
  onRefresh?: () => void;
}

interface IndicatorCardProps {
  title: string;
  indicator: EconomicIndicatorValue | undefined;
  format?: 'percentage' | 'currency' | 'number';
  goodDirection?: 'up' | 'down';
  color?: string;
}

const IndicatorCard: React.FC<IndicatorCardProps> = ({
  title,
  indicator,
  format = 'number',
  goodDirection,
  color = 'primary',
}) => {
  if (!indicator || indicator.value === null) {
    return (
      <Card>
        <CardContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h5" color="text.disabled">
            N/A
          </Typography>
        </CardContent>
      </Card>
    );
  }

  let formattedValue: string;
  switch (format) {
    case 'percentage':
      formattedValue = marketIntelligenceService.formatPercentage(indicator.value, 2);
      break;
    case 'currency':
      formattedValue = marketIntelligenceService.formatCurrency(indicator.value);
      break;
    default:
      formattedValue = marketIntelligenceService.formatNumber(indicator.value);
  }

  const getTrendIcon = () => {
    if (!goodDirection) return <ShowChartIcon />;

    if (goodDirection === 'up') {
      return indicator.value > 0 ? <TrendingUpIcon /> : <TrendingDownIcon />;
    } else {
      return indicator.value > 0 ? <TrendingDownIcon /> : <TrendingUpIcon />;
    }
  };

  const getTrendColor = () => {
    if (!goodDirection) return color;

    if (goodDirection === 'up') {
      return indicator.value > 0 ? 'success' : 'error';
    } else {
      return indicator.value > 0 ? 'error' : 'success';
    }
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2}>
          <Box
            sx={{
              backgroundColor: `${getTrendColor()}.main`,
              color: 'white',
              p: 1.5,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {getTrendIcon()}
          </Box>
          <Box flex={1}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h5" fontWeight="bold">
              {formattedValue}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              As of {marketIntelligenceService.formatVintage(indicator.date)}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

const EconomicIndicatorsPanel: React.FC<EconomicIndicatorsPanelProps> = ({
  data,
  propertyCode,
  onRefresh,
}) => {
  const { data: indicators, lineage } = data;

  const confidenceColor = marketIntelligenceService.getConfidenceBadgeColor(lineage.confidence);

  const hasAnyData = Object.values(indicators).some((ind) => ind && ind.value !== null);

  if (!hasAnyData) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          No economic indicator data available. This may require a FRED API key to be configured.
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Data Source Info */}
      <Box mb={3} display="flex" gap={1} flexWrap="wrap" alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Data Source:
        </Typography>
        <Chip label={lineage.source.toUpperCase()} size="small" />
        <Chip
          label={`Vintage: ${marketIntelligenceService.formatVintage(lineage.vintage)}`}
          size="small"
        />
        <Chip label={`Confidence: ${lineage.confidence}%`} size="small" color={confidenceColor} />
        <Chip
          label={`Fetched: ${new Date(lineage.fetched_at).toLocaleString()}`}
          size="small"
          variant="outlined"
        />
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* National Economic Indicators */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        National Economic Indicators
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="GDP Growth"
            indicator={indicators.gdp_growth}
            format="percentage"
            goodDirection="up"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="Unemployment Rate"
            indicator={indicators.unemployment_rate}
            format="percentage"
            goodDirection="down"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="Inflation Rate (CPI)"
            indicator={indicators.inflation_rate}
            format="percentage"
            goodDirection="down"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="Federal Funds Rate"
            indicator={indicators.fed_funds_rate}
            format="percentage"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="30-Year Mortgage Rate"
            indicator={indicators.mortgage_rate_30y}
            format="percentage"
            goodDirection="down"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <IndicatorCard
            title="Recession Probability"
            indicator={indicators.recession_probability}
            format="percentage"
            goodDirection="down"
          />
        </Grid>
      </Grid>

      {/* MSA-Level Indicators (if available) */}
      {(indicators.msa_unemployment || indicators.msa_gdp) && (
        <>
          <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
            Metropolitan Statistical Area (MSA) Indicators
          </Typography>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {indicators.msa_unemployment && (
              <Grid item xs={12} sm={6} md={4}>
                <IndicatorCard
                  title="MSA Unemployment Rate"
                  indicator={indicators.msa_unemployment}
                  format="percentage"
                  goodDirection="down"
                />
              </Grid>
            )}
            {indicators.msa_gdp && (
              <Grid item xs={12} sm={6} md={4}>
                <IndicatorCard
                  title="MSA GDP Growth"
                  indicator={indicators.msa_gdp}
                  format="percentage"
                  goodDirection="up"
                />
              </Grid>
            )}
          </Grid>
        </>
      )}

      {/* Summary Table */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Detailed View
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableBody>
            {indicators.gdp_growth && (
              <TableRow>
                <TableCell>
                  <strong>GDP Growth</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.gdp_growth.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.gdp_growth.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.unemployment_rate && (
              <TableRow>
                <TableCell>
                  <strong>National Unemployment Rate</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.unemployment_rate.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.unemployment_rate.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.inflation_rate && (
              <TableRow>
                <TableCell>
                  <strong>Inflation Rate (CPI)</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.inflation_rate.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.inflation_rate.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.fed_funds_rate && (
              <TableRow>
                <TableCell>
                  <strong>Federal Funds Rate</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.fed_funds_rate.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.fed_funds_rate.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.mortgage_rate_30y && (
              <TableRow>
                <TableCell>
                  <strong>30-Year Mortgage Rate</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.mortgage_rate_30y.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.mortgage_rate_30y.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.recession_probability && (
              <TableRow>
                <TableCell>
                  <strong>Recession Probability</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(
                    indicators.recession_probability.value || 0,
                    2
                  )}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.recession_probability.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.msa_unemployment && (
              <TableRow>
                <TableCell>
                  <strong>MSA Unemployment Rate</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.msa_unemployment.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.msa_unemployment.date)}
                </TableCell>
              </TableRow>
            )}
            {indicators.msa_gdp && (
              <TableRow>
                <TableCell>
                  <strong>MSA GDP Growth</strong>
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatPercentage(indicators.msa_gdp.value || 0, 2)}
                </TableCell>
                <TableCell align="right">
                  {marketIntelligenceService.formatVintage(indicators.msa_gdp.date)}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default EconomicIndicatorsPanel;
