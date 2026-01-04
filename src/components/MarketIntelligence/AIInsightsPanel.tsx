/**
 * AI Insights Panel
 *
 * Displays AI-generated insights including SWOT analysis, investment recommendations,
 * risk assessment, and market opportunities
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Paper,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  TrendingUp as StrengthIcon,
  Warning as WeaknessIcon,
  EmojiObjects as OpportunityIcon,
  Error as ThreatIcon,
  Assessment as AssessmentIcon,
  Recommend as RecommendIcon,
  Info as InfoIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import type { AIInsights } from '../../types/market-intelligence';

interface AIInsightsPanelProps {
  data: AIInsights;
  propertyCode: string;
  onRefresh?: () => void;
}

interface SWOTSectionProps {
  title: string;
  items: string[];
  icon: React.ReactNode;
  color: string;
  emptyMessage: string;
}

const SWOTSection: React.FC<SWOTSectionProps> = ({ title, items, icon, color, emptyMessage }) => {
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
          <Typography variant="h6" fontWeight="bold">
            {title}
          </Typography>
          <Chip label={items.length} size="small" sx={{ ml: 'auto' }} />
        </Box>
        <Divider sx={{ mb: 2 }} />
        {items.length > 0 ? (
          <List dense disablePadding>
            {items.map((item, index) => (
              <ListItem key={index} disablePadding sx={{ mb: 1 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <CheckIcon sx={{ fontSize: 18, color }} />
                </ListItemIcon>
                <ListItemText primary={item} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary" fontStyle="italic">
            {emptyMessage}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ data }) => {
  const insights = data.data;
  const swot = insights.swot_analysis;
  const recommendation = insights.investment_recommendation;

  const getRecommendationColor = (rec: string): string => {
    if (rec === 'BUY') return '#2e7d32';
    if (rec === 'SELL') return '#d32f2f';
    return '#1976d2';
  };

  const getRecommendationBgColor = (rec: string): string => {
    if (rec === 'BUY') return '#e8f5e9';
    if (rec === 'SELL') return '#ffebee';
    return '#e3f2fd';
  };

  const getConfidenceColor = (score: number): string => {
    if (score >= 70) return '#2e7d32';
    if (score >= 40) return '#ff9800';
    return '#d32f2f';
  };

  return (
    <Box p={3}>
      {/* Investment Recommendation */}
      <Paper
        sx={{
          p: 4,
          mb: 4,
          backgroundColor: getRecommendationBgColor(recommendation.recommendation),
          border: `2px solid ${getRecommendationColor(recommendation.recommendation)}`,
        }}
      >
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <RecommendIcon sx={{ fontSize: 48, color: getRecommendationColor(recommendation.recommendation) }} />
          <Box flex={1}>
            <Typography variant="overline" color="text.secondary">
              Investment Recommendation
            </Typography>
            <Typography variant="h3" fontWeight="bold" color={getRecommendationColor(recommendation.recommendation)}>
              {recommendation.recommendation}
            </Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="caption" color="text.secondary" display="block">
              Confidence Score
            </Typography>
            <Typography variant="h4" fontWeight="bold" color={getConfidenceColor(recommendation.confidence_score)}>
              {recommendation.confidence_score}
              <Typography component="span" variant="h6" color="text.secondary">
                /100
              </Typography>
            </Typography>
          </Box>
        </Box>

        <Typography variant="body1" paragraph sx={{ fontStyle: 'italic' }}>
          "{recommendation.rationale}"
        </Typography>

        {recommendation.key_factors.length > 0 && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Key Factors:
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {recommendation.key_factors.map((factor, index) => (
                <Chip key={index} label={factor} size="small" variant="outlined" />
              ))}
            </Box>
          </Box>
        )}
      </Paper>

      {/* SWOT Analysis */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        SWOT Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Comprehensive analysis of Strengths, Weaknesses, Opportunities, and Threats
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <SWOTSection
            title="Strengths"
            items={swot.strengths}
            icon={<StrengthIcon />}
            color="#2e7d32"
            emptyMessage="No significant strengths identified"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <SWOTSection
            title="Weaknesses"
            items={swot.weaknesses}
            icon={<WeaknessIcon />}
            color="#d32f2f"
            emptyMessage="No significant weaknesses identified"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <SWOTSection
            title="Opportunities"
            items={swot.opportunities}
            icon={<OpportunityIcon />}
            color="#1976d2"
            emptyMessage="No opportunities identified"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <SWOTSection
            title="Threats"
            items={swot.threats}
            icon={<ThreatIcon />}
            color="#ff9800"
            emptyMessage="No threats identified"
          />
        </Grid>
      </Grid>

      {/* Risk Assessment */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Risk Assessment
      </Typography>
      <Paper sx={{ p: 3, mb: 4 }}>
        <Box display="flex" alignItems="flex-start" gap={2}>
          <AssessmentIcon sx={{ fontSize: 32, color: 'primary.main', mt: 0.5 }} />
          <Box>
            <Typography variant="body1">{insights.risk_assessment}</Typography>
          </Box>
        </Box>
      </Paper>

      {/* Value-Creation Opportunities */}
      {insights.opportunities.length > 0 && (
        <>
          <Typography variant="h5" gutterBottom fontWeight="bold">
            Value-Creation Opportunities
          </Typography>
          <Paper sx={{ p: 3, mb: 4 }}>
            <List>
              {insights.opportunities.map((opportunity, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon>
                      <OpportunityIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText primary={opportunity} primaryTypographyProps={{ variant: 'body1' }} />
                  </ListItem>
                  {index < insights.opportunities.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </>
      )}

      {/* Market Trend Synthesis */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Market Trend Synthesis
      </Typography>
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="body1">{insights.market_trend_synthesis}</Typography>
      </Paper>

      {/* Methodology Note */}
      <Alert severity="info" icon={<InfoIcon />}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          AI Insights Methodology
        </Typography>
        <Typography variant="caption">
          These insights are generated by analyzing all available market intelligence data including demographics,
          economic indicators, location intelligence, ESG assessment, forecasts, and competitive positioning. The
          investment recommendation uses a scoring algorithm that weighs strengths, weaknesses, opportunities, and
          threats. In production, these insights can be enhanced with Claude API or GPT-4 for natural language
          generation and deeper analysis.
        </Typography>
      </Alert>

      {/* Data Source */}
      <Box mt={3}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Analysis Engine
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.source}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Analysis Date
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.lineage.vintage}
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
                Total Insights
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {swot.strengths.length + swot.weaknesses.length + swot.opportunities.length + swot.threats.length}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default AIInsightsPanel;
