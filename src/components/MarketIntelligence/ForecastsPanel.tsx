/**
 * Forecasts Panel
 *
 * Displays 12-month predictive forecasts for property metrics including
 * rent growth, occupancy rates, cap rates, and property value
 */

import React from 'react';
import {
  Box,
  Grid,
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
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ChartIcon,
  AttachMoney as MoneyIcon,
  Home as HomeIcon,
  People as PeopleIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import type { Forecasts } from '../../types/market-intelligence';

interface ForecastsPanelProps {
  data: Forecasts;
  propertyCode: string;
  onRefresh?: () => void;
}

interface ForecastCardProps {
  title: string;
  currentValue: string;
  predictedValue: string;
  changePercent: number;
  confidenceInterval: [number, number];
  model: string;
  accuracy?: number;
  icon: React.ReactNode;
  color: string;
  formatValue: (val: number) => string;
}

const ForecastCard: React.FC<ForecastCardProps> = ({
  title,
  currentValue,
  predictedValue,
  changePercent,
  confidenceInterval,
  model,
  accuracy,
  icon,
  color,
  formatValue,
}) => {
  const isPositive = changePercent >= 0;
  const changeColor = isPositive ? '#2e7d32' : '#d32f2f';

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
            <Typography variant="h5" fontWeight="bold">
              {predictedValue}
            </Typography>
            <Box display="flex" alignItems="center" gap={1} mt={0.5}>
              {isPositive ? (
                <TrendingUpIcon sx={{ fontSize: 20, color: changeColor }} />
              ) : (
                <TrendingDownIcon sx={{ fontSize: 20, color: changeColor }} />
              )}
              <Typography variant="body2" sx={{ color: changeColor, fontWeight: 'bold' }}>
                {isPositive ? '+' : ''}
                {changePercent.toFixed(1)}%
              </Typography>
            </Box>
          </Box>
        </Box>

        <Box mb={2}>
          <Typography variant="caption" color="text.secondary" display="block">
            Current: {currentValue}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            95% CI: {formatValue(confidenceInterval[0])} - {formatValue(confidenceInterval[1])}
          </Typography>
        </Box>

        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Chip label={model} size="small" variant="outlined" />
          {accuracy && (
            <Typography variant="caption" color="text.secondary">
              Accuracy: {(accuracy * 100).toFixed(0)}%
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

const ForecastsPanel: React.FC<ForecastsPanelProps> = ({ data }) => {
  const forecasts = data.data;

  // Helper functions
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  const formatNumber = (value: number): string => {
    return value.toFixed(1);
  };

  return (
    <Box p={3}>
      {/* Header */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        12-Month Forecasts
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Predictive projections for key property metrics with confidence intervals
      </Typography>

      {/* Forecast Cards */}
      <Grid container spacing={3} mb={4}>
        {forecasts.rent_forecast_12mo && (
          <Grid item xs={12} md={6}>
            <ForecastCard
              title="Average Rent"
              currentValue={formatCurrency(
                forecasts.rent_forecast_12mo.predicted_rent! / (1 + forecasts.rent_forecast_12mo.change_pct! / 100)
              )}
              predictedValue={formatCurrency(forecasts.rent_forecast_12mo.predicted_rent!)}
              changePercent={forecasts.rent_forecast_12mo.change_pct!}
              confidenceInterval={forecasts.rent_forecast_12mo.confidence_interval_95}
              model={forecasts.rent_forecast_12mo.model}
              accuracy={forecasts.rent_forecast_12mo.r_squared}
              icon={<MoneyIcon />}
              color="#1976d2"
              formatValue={formatCurrency}
            />
          </Grid>
        )}

        {forecasts.occupancy_forecast_12mo && (
          <Grid item xs={12} md={6}>
            <ForecastCard
              title="Occupancy Rate"
              currentValue={formatPercent(
                forecasts.occupancy_forecast_12mo.predicted_occupancy! / (1 + forecasts.occupancy_forecast_12mo.change_pct! / 100)
              )}
              predictedValue={formatPercent(forecasts.occupancy_forecast_12mo.predicted_occupancy!)}
              changePercent={forecasts.occupancy_forecast_12mo.change_pct!}
              confidenceInterval={forecasts.occupancy_forecast_12mo.confidence_interval_95}
              model={forecasts.occupancy_forecast_12mo.model}
              accuracy={forecasts.occupancy_forecast_12mo.accuracy}
              icon={<PeopleIcon />}
              color="#9c27b0"
              formatValue={formatNumber}
            />
          </Grid>
        )}

        {forecasts.cap_rate_forecast_12mo && (
          <Grid item xs={12} md={6}>
            <ForecastCard
              title="Cap Rate"
              currentValue={formatPercent(
                forecasts.cap_rate_forecast_12mo.predicted_cap_rate! - (forecasts.cap_rate_forecast_12mo.change_bps! / 100)
              )}
              predictedValue={formatPercent(forecasts.cap_rate_forecast_12mo.predicted_cap_rate!)}
              changePercent={(forecasts.cap_rate_forecast_12mo.change_bps! / 100) * 20} // Convert bps to percentage change
              confidenceInterval={forecasts.cap_rate_forecast_12mo.confidence_interval_95}
              model={forecasts.cap_rate_forecast_12mo.model}
              accuracy={forecasts.cap_rate_forecast_12mo.r_squared}
              icon={<ChartIcon />}
              color="#ff9800"
              formatValue={formatNumber}
            />
          </Grid>
        )}

        {forecasts.value_forecast_12mo && (
          <Grid item xs={12} md={6}>
            <ForecastCard
              title="Property Value"
              currentValue={formatCurrency(
                forecasts.value_forecast_12mo.predicted_value! / (1 + forecasts.value_forecast_12mo.change_pct! / 100)
              )}
              predictedValue={formatCurrency(forecasts.value_forecast_12mo.predicted_value!)}
              changePercent={forecasts.value_forecast_12mo.change_pct!}
              confidenceInterval={forecasts.value_forecast_12mo.confidence_interval_95}
              model={forecasts.value_forecast_12mo.model}
              accuracy={forecasts.value_forecast_12mo.r_squared}
              icon={<HomeIcon />}
              color="#00796b"
              formatValue={formatCurrency}
            />
          </Grid>
        )}
      </Grid>

      {/* Model Details Table */}
      <Typography variant="h6" gutterBottom fontWeight="bold">
        Model Performance Metrics
      </Typography>
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Metric</strong>
              </TableCell>
              <TableCell>
                <strong>Model</strong>
              </TableCell>
              <TableCell align="right">
                <strong>R² / Accuracy</strong>
              </TableCell>
              <TableCell align="right">
                <strong>MAE</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {forecasts.rent_forecast_12mo && (
              <TableRow>
                <TableCell>Rent Forecast</TableCell>
                <TableCell>
                  <Chip label={forecasts.rent_forecast_12mo.model} size="small" />
                </TableCell>
                <TableCell align="right">
                  {forecasts.rent_forecast_12mo.r_squared?.toFixed(2) || 'N/A'}
                </TableCell>
                <TableCell align="right">
                  {forecasts.rent_forecast_12mo.mae ? formatCurrency(forecasts.rent_forecast_12mo.mae) : 'N/A'}
                </TableCell>
              </TableRow>
            )}
            {forecasts.occupancy_forecast_12mo && (
              <TableRow>
                <TableCell>Occupancy Forecast</TableCell>
                <TableCell>
                  <Chip label={forecasts.occupancy_forecast_12mo.model} size="small" />
                </TableCell>
                <TableCell align="right">
                  {forecasts.occupancy_forecast_12mo.accuracy?.toFixed(2) || 'N/A'}
                </TableCell>
                <TableCell align="right">
                  {forecasts.occupancy_forecast_12mo.mae ? `${forecasts.occupancy_forecast_12mo.mae.toFixed(1)}%` : 'N/A'}
                </TableCell>
              </TableRow>
            )}
            {forecasts.cap_rate_forecast_12mo && (
              <TableRow>
                <TableCell>Cap Rate Forecast</TableCell>
                <TableCell>
                  <Chip label={forecasts.cap_rate_forecast_12mo.model} size="small" />
                </TableCell>
                <TableCell align="right">
                  {forecasts.cap_rate_forecast_12mo.r_squared?.toFixed(2) || 'N/A'}
                </TableCell>
                <TableCell align="right">N/A</TableCell>
              </TableRow>
            )}
            {forecasts.value_forecast_12mo && (
              <TableRow>
                <TableCell>Value Forecast</TableCell>
                <TableCell>
                  <Chip label={forecasts.value_forecast_12mo.model} size="small" />
                </TableCell>
                <TableCell align="right">
                  {forecasts.value_forecast_12mo.r_squared?.toFixed(2) || 'N/A'}
                </TableCell>
                <TableCell align="right">N/A</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Methodology Note */}
      <Alert severity="info" icon={<InfoIcon />}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          Forecasting Methodology
        </Typography>
        <Typography variant="caption">
          These forecasts use statistical models to project future performance based on historical trends and economic
          indicators. The 95% confidence intervals indicate the range within which actual values are likely to fall.
          In production, these models can be enhanced with Prophet, ARIMA, XGBoost, or LSTM for improved accuracy.
        </Typography>
      </Alert>

      {/* Data Source Information */}
      <Box mt={3}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Data Source
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.source}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Forecast Horizon
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                12 months
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Confidence Level
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.confidence}%
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Generated
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {new Date(data.lineage.fetched_at).toLocaleDateString()}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default ForecastsPanel;
