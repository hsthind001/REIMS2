/**
 * ESG Assessment Panel
 *
 * Displays Environmental, Social, and Governance risk assessments
 * including climate risks, social factors, and governance compliance
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
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  Nature as EcoIcon,
  People as PeopleIcon,
  Gavel as GavelIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  LocalFireDepartment as FireIcon,
  Water as FloodIcon,
  Landscape as EarthquakeIcon,
} from '@mui/icons-material';
import type { ESGAssessment } from '../../types/market-intelligence';

interface ESGAssessmentPanelProps {
  data: ESGAssessment;
  propertyCode: string;
  onRefresh?: () => void;
}

interface ScoreCardProps {
  title: string;
  score: number;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const ScoreCard: React.FC<ScoreCardProps> = ({ title, score, description, icon, color }) => {
  const getScoreLabel = (score: number): string => {
    if (score >= 80) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 60) return 'Fair';
    if (score >= 50) return 'Poor';
    return 'Critical';
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return '#2e7d32';
    if (score >= 70) return '#66bb6a';
    if (score >= 60) return '#ffa726';
    if (score >= 50) return '#ff9800';
    return '#f44336';
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
              {score}/100
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

const ESGAssessmentPanel: React.FC<ESGAssessmentPanelProps> = ({ data }) => {
  const environmental = data.data.environmental;
  const social = data.data.social;
  const governance = data.data.governance;

  const getRiskSeverity = (score: number): 'success' | 'warning' | 'error' => {
    if (score < 30) return 'success';
    if (score < 60) return 'warning';
    return 'error';
  };

  return (
    <Box p={3}>
      {/* Overall ESG Score */}
      <Box mb={4}>
        <Typography variant="h4" gutterBottom fontWeight="bold">
          ESG Rating: {data.data.esg_grade}
        </Typography>
        <Typography variant="h6" color="text.secondary" paragraph>
          Overall ESG Score: {data.data.composite_esg_score}/100
        </Typography>
        <LinearProgress
          variant="determinate"
          value={data.data.composite_esg_score}
          sx={{
            height: 12,
            borderRadius: 6,
            backgroundColor: '#e0e0e0',
            '& .MuiLinearProgress-bar': {
              backgroundColor:
                data.data.composite_esg_score >= 80
                  ? '#2e7d32'
                  : data.data.composite_esg_score >= 60
                  ? '#66bb6a'
                  : '#ff9800',
            },
          }}
        />
        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          Composite score based on Environmental (40%), Social (35%), and Governance (25%) factors
        </Typography>
      </Box>

      {/* Component Scores */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        ESG Component Scores
      </Typography>
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Environmental"
            score={environmental.composite_score ?? 0}
            icon={<EcoIcon />}
            description="Climate risks, energy efficiency, and environmental impact"
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Social"
            score={social.composite_score ?? 0}
            icon={<PeopleIcon />}
            description="Community safety, schools, health, and inequality"
            color="#2196f3"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard
            title="Governance"
            score={governance.composite_score ?? 0}
            icon={<GavelIcon />}
            description="Zoning compliance, permits, taxes, and legal standing"
            color="#9c27b0"
          />
        </Grid>
      </Grid>

      {/* Environmental Risk Details */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Environmental Risk Assessment
      </Typography>
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={1}>
                <FloodIcon color={getRiskSeverity(environmental.flood_risk_score)} />
                <Typography variant="h6">Flood Risk</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {environmental.flood_risk_score}/100
              </Typography>
              <Chip
                label={environmental.flood_zone}
                size="small"
                color={getRiskSeverity(environmental.flood_risk_score)}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={1}>
                <FireIcon color={getRiskSeverity(environmental.wildfire_risk_score)} />
                <Typography variant="h6">Wildfire Risk</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {environmental.wildfire_risk_score}/100
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Higher score indicates greater risk
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={1}>
                <EarthquakeIcon color={getRiskSeverity(environmental.earthquake_risk_score)} />
                <Typography variant="h6">Earthquake Risk</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {environmental.earthquake_risk_score}/100
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Based on seismic activity zones
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Energy & Emissions */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Energy Efficiency Rating
            </Typography>
            <Typography variant="h3" fontWeight="bold" color="primary">
              {environmental.energy_efficiency_rating}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Building energy performance grade
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Carbon Emissions Intensity
            </Typography>
            <Typography variant="h3" fontWeight="bold">
              {environmental.emissions_intensity_kg_co2_sqft.toFixed(2)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              kg CO₂/sq ft annually
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Social Risk Details */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Social Risk Assessment
      </Typography>
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Factor</strong>
              </TableCell>
              <TableCell align="right">
                <strong>Score/Value</strong>
              </TableCell>
              <TableCell>
                <strong>Status</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>Crime Score</TableCell>
              <TableCell align="right">{social.crime_score}/100</TableCell>
              <TableCell>
                <Chip
                  label={social.crime_score < 30 ? 'Low' : social.crime_score < 60 ? 'Moderate' : 'High'}
                  color={getRiskSeverity(social.crime_score)}
                  size="small"
                />
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>School Quality</TableCell>
              <TableCell align="right">{social.school_quality_score}/100</TableCell>
              <TableCell>
                <Chip
                  label={social.school_quality_score >= 80 ? 'Excellent' : social.school_quality_score >= 60 ? 'Good' : 'Fair'}
                  color={social.school_quality_score >= 60 ? 'success' : 'warning'}
                  size="small"
                />
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Income Inequality (Gini)</TableCell>
              <TableCell align="right">{social.income_inequality_gini.toFixed(2)}</TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  0 = perfect equality, 1 = perfect inequality
                </Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Diversity Index</TableCell>
              <TableCell align="right">{(social.diversity_index * 100).toFixed(0)}%</TableCell>
              <TableCell>
                <Chip
                  label={social.diversity_index >= 0.6 ? 'High' : social.diversity_index >= 0.4 ? 'Moderate' : 'Low'}
                  color={social.diversity_index >= 0.5 ? 'success' : 'warning'}
                  size="small"
                />
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Community Health</TableCell>
              <TableCell align="right">{social.community_health_score}/100</TableCell>
              <TableCell>
                <Chip
                  label={social.community_health_score >= 70 ? 'Good' : social.community_health_score >= 50 ? 'Fair' : 'Poor'}
                  color={social.community_health_score >= 60 ? 'success' : 'warning'}
                  size="small"
                />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>

      {/* Governance Risk Details */}
      <Typography variant="h5" gutterBottom fontWeight="bold">
        Governance Risk Assessment
      </Typography>
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Zoning Compliance</Typography>
                {governance.zoning_compliance_score >= 80 ? (
                  <CheckIcon color="success" />
                ) : (
                  <WarningIcon color="warning" />
                )}
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {governance.zoning_compliance_score}/100
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Municipal zoning compliance score
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Permit History</Typography>
                {governance.permit_history_score >= 80 ? (
                  <CheckIcon color="success" />
                ) : (
                  <WarningIcon color="warning" />
                )}
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {governance.permit_history_score}/100
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Based on permit violations and compliance
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Tax Delinquency Risk
              </Typography>
              <Chip
                label={governance.tax_delinquency_risk}
                color={
                  governance.tax_delinquency_risk === 'Low'
                    ? 'success'
                    : governance.tax_delinquency_risk === 'Medium'
                    ? 'warning'
                    : 'error'
                }
              />
              <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                Property tax payment risk level
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Legal Issues
              </Typography>
              <Typography variant="h4" fontWeight="bold">
                {governance.legal_issues_count}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Open legal matters or disputes
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Data Source Information */}
      <Alert severity="info" sx={{ mt: 4 }}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          ESG Assessment Methodology
        </Typography>
        <Typography variant="caption">
          This assessment combines environmental risk modeling, social indicators, and governance compliance data.
          Scores are calculated using industry-standard ESG frameworks. In production, this integrates with FEMA flood
          maps, USGS earthquake data, FBI crime statistics, GreatSchools ratings, and municipal compliance databases.
        </Typography>
      </Alert>
    </Box>
  );
};

export default ESGAssessmentPanel;
