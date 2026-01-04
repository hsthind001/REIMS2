/**
 * Data Lineage Panel Component
 *
 * Displays audit trail and data lineage information for market intelligence data
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import type { LineageResponse, LineageRecord } from '../../types/market-intelligence';
import * as marketIntelligenceService from '../../services/marketIntelligenceService';

interface DataLineagePanelProps {
  propertyCode: string;
}

const DataLineagePanel: React.FC<DataLineagePanelProps> = ({ propertyCode }) => {
  const [lineageData, setLineageData] = useState<LineageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  useEffect(() => {
    loadLineageData();
  }, [propertyCode, categoryFilter]);

  const loadLineageData = async () => {
    try {
      setLoading(true);
      setError(null);
      const options = categoryFilter !== 'all' ? { category: categoryFilter } : {};
      const data = await marketIntelligenceService.getDataLineage(propertyCode, options);
      setLineageData(data);
    } catch (err: any) {
      console.error('Error loading lineage data:', err);
      setError(err.response?.data?.detail || 'Failed to load lineage data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <SuccessIcon color="success" fontSize="small" />;
      case 'partial':
        return <WarningIcon color="warning" fontSize="small" />;
      case 'failure':
        return <ErrorIcon color="error" fontSize="small" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'success':
        return 'success';
      case 'partial':
        return 'warning';
      case 'failure':
        return 'error';
      default:
        return 'default';
    }
  };

  const getConfidenceColor = (confidence: number | null): 'success' | 'warning' | 'error' | 'default' => {
    if (confidence === null) return 'default';
    if (confidence >= 90) return 'success';
    if (confidence >= 70) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!lineageData || lineageData.lineage.length === 0) {
    return (
      <Box p={3}>
        <Alert severity="info">No data lineage records found for this property.</Alert>
      </Box>
    );
  }

  // Calculate statistics
  const successCount = lineageData.lineage.filter((l) => l.status === 'success').length;
  const partialCount = lineageData.lineage.filter((l) => l.status === 'partial').length;
  const failureCount = lineageData.lineage.filter((l) => l.status === 'failure').length;

  const categories = Array.from(new Set(lineageData.lineage.map((l) => l.category)));

  return (
    <Box p={3}>
      {/* Summary Statistics */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Data Lineage Summary
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Total Records
              </Typography>
              <Typography variant="h4" fontWeight="bold">
                {lineageData.total_records}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderTop: 3, borderColor: 'success.main' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Successful
              </Typography>
              <Typography variant="h4" fontWeight="bold" color="success.main">
                {successCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderTop: 3, borderColor: 'warning.main' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Partial
              </Typography>
              <Typography variant="h4" fontWeight="bold" color="warning.main">
                {partialCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderTop: 3, borderColor: 'error.main' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Failed
              </Typography>
              <Typography variant="h4" fontWeight="bold" color="error.main">
                {failureCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filter */}
      <Box mb={3}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Category</InputLabel>
          <Select
            value={categoryFilter}
            label="Filter by Category"
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <MenuItem value="all">All Categories</MenuItem>
            {categories.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Lineage Table */}
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Audit Trail
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Status</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Vintage</TableCell>
              <TableCell>Fetched At</TableCell>
              <TableCell align="right">Confidence</TableCell>
              <TableCell align="right">Records</TableCell>
              <TableCell>Error</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {lineageData.lineage.map((record: LineageRecord) => (
              <TableRow key={record.id} hover>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(record.status)}
                    <Chip label={record.status} size="small" color={getStatusColor(record.status)} />
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip label={record.source} size="small" variant="outlined" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{record.category}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {record.vintage
                      ? marketIntelligenceService.formatVintage(record.vintage)
                      : 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {new Date(record.fetched_at).toLocaleString()}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {record.confidence !== null ? (
                    <Chip
                      label={`${record.confidence}%`}
                      size="small"
                      color={getConfidenceColor(record.confidence)}
                    />
                  ) : (
                    <Typography variant="body2" color="text.disabled">
                      N/A
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">
                    {record.records_fetched !== null
                      ? marketIntelligenceService.formatNumber(record.records_fetched)
                      : 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell>
                  {record.error ? (
                    <Typography variant="body2" color="error">
                      {record.error}
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.disabled">
                      -
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DataLineagePanel;
