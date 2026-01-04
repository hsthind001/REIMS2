/**
 * Market Intelligence Dashboard
 *
 * Main dashboard for viewing comprehensive market intelligence data for properties
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Tabs,
  Tab,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  IconButton,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  LocationOn as LocationIcon,
  Assessment as AssessmentIcon,
  Nature as EcoIcon,
  Timeline as TimelineIcon,
  CompareArrows as CompetitiveIcon,
  Psychology as AIIcon,
  History as HistoryIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import type { MarketIntelligence, RefreshRequest } from '../types/market-intelligence';
import * as marketIntelligenceService from '../services/marketIntelligenceService';
import DemographicsPanel from '../components/MarketIntelligence/DemographicsPanel';
import EconomicIndicatorsPanel from '../components/MarketIntelligence/EconomicIndicatorsPanel';
import LocationIntelligencePanel from '../components/MarketIntelligence/LocationIntelligencePanel';
import ESGAssessmentPanel from '../components/MarketIntelligence/ESGAssessmentPanel';
import ForecastsPanel from '../components/MarketIntelligence/ForecastsPanel';
import CompetitiveAnalysisPanel from '../components/MarketIntelligence/CompetitiveAnalysisPanel';
import AIInsightsPanel from '../components/MarketIntelligence/AIInsightsPanel';
import DataLineagePanel from '../components/MarketIntelligence/DataLineagePanel';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`market-intel-tabpanel-${index}`}
      aria-labelledby={`market-intel-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const MarketIntelligenceDashboard: React.FC = () => {
  // Extract property code from hash route (e.g., #market-intelligence/ESP001)
  const getPropertyCodeFromHash = () => {
    const hash = window.location.hash.slice(1); // Remove #
    const parts = hash.split('/');
    return parts.length > 1 ? parts[1] : null;
  };

  const [propertyCode, setPropertyCode] = useState<string | null>(getPropertyCodeFromHash());
  const [activeTab, setActiveTab] = useState(0);
  const [marketIntel, setMarketIntel] = useState<MarketIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleHashChange = () => {
      setPropertyCode(getPropertyCodeFromHash());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (propertyCode) {
      loadMarketIntelligence();
    }
  }, [propertyCode]);

  const loadMarketIntelligence = async () => {
    if (!propertyCode) return;

    try {
      setLoading(true);
      setError(null);
      const data = await marketIntelligenceService.getMarketIntelligence(propertyCode);
      setMarketIntel(data);
    } catch (err: any) {
      console.error('Error loading market intelligence:', err);
      // Handle different error response formats
      let errorMessage = 'Failed to load market intelligence data';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          // Handle Pydantic validation errors (array of objects)
          errorMessage = err.response.data.detail
            .map((e: any) => `${e.loc?.join(' > ') || 'Field'}: ${e.msg}`)
            .join(', ');
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async (categories?: RefreshRequest['categories']) => {
    if (!propertyCode) return;

    try {
      setRefreshing(true);
      setError(null);
      await marketIntelligenceService.refreshMarketIntelligence(propertyCode, { categories });
      await loadMarketIntelligence();
    } catch (err: any) {
      console.error('Error refreshing market intelligence:', err);
      // Handle different error response formats
      let errorMessage = 'Failed to refresh market intelligence data';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          // Handle Pydantic validation errors (array of objects)
          errorMessage = err.response.data.detail
            .map((e: any) => `${e.loc?.join(' > ') || 'Field'}: ${e.msg}`)
            .join(', ');
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setRefreshing(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="contained" onClick={loadMarketIntelligence}>
          Retry
        </Button>
      </Container>
    );
  }

  if (!marketIntel) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="info">No market intelligence data available for this property.</Alert>
      </Container>
    );
  }

  const needsRefresh = marketIntel.last_refreshed
    ? marketIntelligenceService.needsRefresh(marketIntel.last_refreshed)
    : true;

  const handleBack = () => {
    window.history.back();
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <Box display="flex" alignItems="center" gap={2}>
              <IconButton
                onClick={handleBack}
                sx={{
                  backgroundColor: 'primary.main',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                }}
                size="large"
              >
                <ArrowBackIcon />
              </IconButton>
              <Box>
                <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
                  Market Intelligence
                </Typography>
                <Typography variant="subtitle1" color="text.secondary">
                  Property: {marketIntel.property_code}
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} md={6} sx={{ textAlign: { xs: 'left', md: 'right' } }}>
            <Box display="flex" gap={2} justifyContent={{ xs: 'flex-start', md: 'flex-end' }} flexWrap="wrap">
              {marketIntel.last_refreshed && (
                <Chip
                  label={`Last Updated: ${new Date(marketIntel.last_refreshed).toLocaleDateString()}`}
                  color={needsRefresh ? 'warning' : 'success'}
                  size="small"
                />
              )}
              {marketIntel.refresh_status && (
                <Chip
                  label={`Status: ${marketIntel.refresh_status}`}
                  color={
                    marketIntel.refresh_status === 'success'
                      ? 'success'
                      : marketIntel.refresh_status === 'partial'
                      ? 'warning'
                      : 'error'
                  }
                  size="small"
                />
              )}
              <Button
                variant="contained"
                startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
                onClick={() => handleRefresh()}
                disabled={refreshing}
              >
                {refreshing ? 'Refreshing...' : 'Refresh All'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Main Content */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="market intelligence tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab
            icon={<LocationIcon />}
            label="Demographics"
            iconPosition="start"
            disabled={!marketIntel.demographics}
          />
          <Tab
            icon={<TrendingUpIcon />}
            label="Economic Indicators"
            iconPosition="start"
            disabled={!marketIntel.economic_indicators}
          />
          <Tab
            icon={<AssessmentIcon />}
            label="Location Intelligence"
            iconPosition="start"
            disabled={!marketIntel.location_intelligence}
          />
          <Tab
            icon={<EcoIcon />}
            label="ESG Assessment"
            iconPosition="start"
            disabled={!marketIntel.esg_assessment}
          />
          <Tab
            icon={<TimelineIcon />}
            label="Forecasts"
            iconPosition="start"
            disabled={!marketIntel.forecasts}
          />
          <Tab
            icon={<CompetitiveIcon />}
            label="Competitive Analysis"
            iconPosition="start"
            disabled={!marketIntel.competitive_analysis}
          />
          <Tab
            icon={<AIIcon />}
            label="AI Insights"
            iconPosition="start"
            disabled={!marketIntel.ai_insights}
          />
          <Tab icon={<HistoryIcon />} label="Data Lineage" iconPosition="start" />
        </Tabs>

        <Divider />

        {/* Demographics Tab */}
        <TabPanel value={activeTab} index={0}>
          {marketIntel.demographics ? (
            <DemographicsPanel
              data={marketIntel.demographics}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['demographics'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No demographics data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['demographics'])}
                disabled={refreshing}
              >
                Fetch Demographics Data
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Economic Indicators Tab */}
        <TabPanel value={activeTab} index={1}>
          {marketIntel.economic_indicators ? (
            <EconomicIndicatorsPanel
              data={marketIntel.economic_indicators}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['economic'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No economic indicators data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['economic'])}
                disabled={refreshing}
              >
                Fetch Economic Data
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Location Intelligence Tab */}
        <TabPanel value={activeTab} index={2}>
          {marketIntel.location_intelligence ? (
            <LocationIntelligencePanel
              data={marketIntel.location_intelligence}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['location'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No location intelligence data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['location'])}
                disabled={refreshing}
              >
                Fetch Location Intelligence
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* ESG Assessment Tab */}
        <TabPanel value={activeTab} index={3}>
          {marketIntel.esg_assessment ? (
            <ESGAssessmentPanel
              data={marketIntel.esg_assessment}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['esg'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No ESG assessment data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['esg'])}
                disabled={refreshing}
              >
                Fetch ESG Assessment
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Forecasts Tab */}
        <TabPanel value={activeTab} index={4}>
          {marketIntel.forecasts ? (
            <ForecastsPanel
              data={marketIntel.forecasts}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['forecasts'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No forecast data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['forecasts'])}
                disabled={refreshing}
              >
                Generate Forecasts
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Competitive Analysis Tab */}
        <TabPanel value={activeTab} index={5}>
          {marketIntel.competitive_analysis ? (
            <CompetitiveAnalysisPanel
              data={marketIntel.competitive_analysis}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['competitive'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No competitive analysis data available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['competitive'])}
                disabled={refreshing}
              >
                Generate Competitive Analysis
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* AI Insights Tab */}
        <TabPanel value={activeTab} index={6}>
          {marketIntel.ai_insights ? (
            <AIInsightsPanel
              data={marketIntel.ai_insights}
              propertyCode={marketIntel.property_code}
              onRefresh={() => handleRefresh(['insights'])}
            />
          ) : (
            <Box p={3}>
              <Alert severity="info" sx={{ mb: 2 }}>
                No AI insights available for this property.
              </Alert>
              <Button
                variant="contained"
                onClick={() => handleRefresh(['insights'])}
                disabled={refreshing}
              >
                Generate AI Insights
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Data Lineage Tab */}
        <TabPanel value={activeTab} index={7}>
          {propertyCode && <DataLineagePanel propertyCode={propertyCode} />}
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default MarketIntelligenceDashboard;
