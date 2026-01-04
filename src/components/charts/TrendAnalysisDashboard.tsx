/**
 * Trend Analysis Dashboard Component
 * 
 * Comprehensive dashboard showing multiple financial metric trends
 */

import { useState, useEffect } from 'react';
import TrendAnalysisChart from './TrendAnalysisChart';
import type { TrendDataPoint } from './TrendAnalysisChart';
import { Card, Button } from '../design-system';
import { Calendar, TrendingUp, BarChart3 } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface TrendAnalysisDashboardProps {
  /** Property ID (optional, for property-specific trends) */
  propertyId?: number;
  /** Number of months to display */
  months?: number;
  /** Metrics to display */
  metrics?: ('noi' | 'dscr' | 'occupancy' | 'revenue' | 'expenses')[];
}

export default function TrendAnalysisDashboard({
  propertyId,
  months = 12,
  metrics = ['noi', 'dscr', 'occupancy', 'revenue']
}: TrendAnalysisDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [noiData, setNoiData] = useState<TrendDataPoint[]>([]);
  const [dscrData, setDscrData] = useState<TrendDataPoint[]>([]);
  const [occupancyData, setOccupancyData] = useState<TrendDataPoint[]>([]);
  const [revenueData, setRevenueData] = useState<TrendDataPoint[]>([]);
  const [expensesData, setExpensesData] = useState<TrendDataPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTrendData();
  }, [propertyId, months]);

  const loadTrendData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load NOI trend
      if (metrics.includes('noi')) {
        await loadNOITrend();
      }

      // Load DSCR trend
      if (metrics.includes('dscr')) {
        await loadDSCRTrend();
      }

      // Load Occupancy trend
      if (metrics.includes('occupancy')) {
        await loadOccupancyTrend();
      }

      // Load Revenue trend
      if (metrics.includes('revenue')) {
        await loadRevenueTrend();
      }

      // Load Expenses trend
      if (metrics.includes('expenses')) {
        await loadExpensesTrend();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load trend data');
      console.error('Error loading trend data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadNOITrend = async () => {
    try {
      // Use the existing trends endpoint
      if (propertyId) {
        // Get property code first
        const propResponse = await fetch(`${API_BASE_URL}/properties/${propertyId}`, { credentials: 'include' });
        if (propResponse.ok) {
          const prop = await propResponse.json();
          const trendsResponse = await fetch(
            `${API_BASE_URL}/metrics/${prop.property_code}/trends?start_year=${new Date().getFullYear() - Math.ceil(months / 12)}`,
            { credentials: 'include' }
          );
          if (trendsResponse.ok) {
            const trends = await trendsResponse.json();
            const noiPoints = trends.slice(-months).map((item: any) => ({
              date: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              period: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              value: item.net_operating_income || 0
            }));
            setNoiData(noiPoints);
          }
        }
      } else {
        // Portfolio view - aggregate from all properties
        const response = await fetch(`${API_BASE_URL}/metrics/portfolio-changes`, { credentials: 'include' });
        if (response.ok) {
          // For portfolio, we'd need a different endpoint or aggregate manually
          // For now, use empty data
          setNoiData([]);
        }
      }
    } catch (err) {
      console.error('Error loading NOI trend:', err);
    }
  };

  const loadDSCRTrend = async () => {
    try {
      if (!propertyId) return;
      
      const response = await fetch(`${API_BASE_URL}/metrics/${propertyId}/dscr/historical?months=${months}`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setDscrData(data.history?.map((item: any) => ({
          date: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
          period: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
          value: item.dscr || 0
        })) || []);
      }
    } catch (err) {
      console.error('Error loading DSCR trend:', err);
    }
  };

  const loadOccupancyTrend = async () => {
    try {
      if (propertyId) {
        // Get property code first
        const propResponse = await fetch(`${API_BASE_URL}/properties/${propertyId}`, { credentials: 'include' });
        if (propResponse.ok) {
          const prop = await propResponse.json();
          const trendsResponse = await fetch(
            `${API_BASE_URL}/metrics/${prop.property_code}/trends?start_year=${new Date().getFullYear() - Math.ceil(months / 12)}`,
            { credentials: 'include' }
          );
          if (trendsResponse.ok) {
            const trends = await trendsResponse.json();
            const occupancyPoints = trends.slice(-months).map((item: any) => ({
              date: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              period: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              value: item.occupancy_rate || 0
            }));
            setOccupancyData(occupancyPoints);
          }
        }
      } else {
        setOccupancyData([]);
      }
    } catch (err) {
      console.error('Error loading occupancy trend:', err);
    }
  };

  const loadRevenueTrend = async () => {
    try {
      if (propertyId) {
        // Get property code first
        const propResponse = await fetch(`${API_BASE_URL}/properties/${propertyId}`, { credentials: 'include' });
        if (propResponse.ok) {
          const prop = await propResponse.json();
          const trendsResponse = await fetch(
            `${API_BASE_URL}/metrics/${prop.property_code}/trends?start_year=${new Date().getFullYear() - Math.ceil(months / 12)}`,
            { credentials: 'include' }
          );
          if (trendsResponse.ok) {
            const trends = await trendsResponse.json();
            const revenuePoints = trends.slice(-months).map((item: any) => ({
              date: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              period: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              value: item.total_revenue || 0
            }));
            setRevenueData(revenuePoints);
          }
        }
      } else {
        setRevenueData([]);
      }
    } catch (err) {
      console.error('Error loading revenue trend:', err);
    }
  };

  const loadExpensesTrend = async () => {
    try {
      if (propertyId) {
        // Get property code first
        const propResponse = await fetch(`${API_BASE_URL}/properties/${propertyId}`, { credentials: 'include' });
        if (propResponse.ok) {
          const prop = await propResponse.json();
          const trendsResponse = await fetch(
            `${API_BASE_URL}/metrics/${prop.property_code}/trends?start_year=${new Date().getFullYear() - Math.ceil(months / 12)}`,
            { credentials: 'include' }
          );
          if (trendsResponse.ok) {
            const trends = await trendsResponse.json();
            const expensesPoints = trends.slice(-months).map((item: any) => ({
              date: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              period: `${item.period_year}-${String(item.period_month).padStart(2, '0')}`,
              value: item.total_operating_expenses || 0
            }));
            setExpensesData(expensesPoints);
          }
        }
      } else {
        setExpensesData([]);
      }
    } catch (err) {
      console.error('Error loading expenses trend:', err);
    }
  };

  if (loading) {
    return (
      <div className="card p-6">
        <div className="text-center py-8">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Loading trend data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-center py-8 text-red-600">
          <p>Error: {error}</p>
          <Button
            variant="secondary"
            size="sm"
            onClick={loadTrendData}
            className="mt-4"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <BarChart3 className="w-6 h-6" />
          Financial Trends Analysis
        </h2>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Calendar className="w-4 h-4" />
          <span>Last {months} months</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {metrics.includes('noi') && (
          <TrendAnalysisChart
            title="Net Operating Income (NOI) Trend"
            data={noiData}
            metric="NOI"
            chartType="area"
            yAxisLabel="NOI ($)"
            color="#10b981"
            referenceLine={propertyId ? undefined : 0}
            showExport={true}
            height={300}
          />
        )}

        {metrics.includes('dscr') && propertyId && (
          <TrendAnalysisChart
            title="Debt Service Coverage Ratio (DSCR) Trend"
            data={dscrData}
            metric="DSCR"
            chartType="line"
            yAxisLabel="DSCR"
            color="#3b82f6"
            referenceLine={1.25}
            referenceLineLabel="Covenant Threshold"
            showExport={true}
            height={300}
          />
        )}

        {metrics.includes('occupancy') && (
          <TrendAnalysisChart
            title="Occupancy Rate Trend"
            data={occupancyData}
            metric="Occupancy"
            chartType="area"
            yAxisLabel="Occupancy (%)"
            color="#8b5cf6"
            showExport={true}
            height={300}
          />
        )}

        {metrics.includes('revenue') && (
          <TrendAnalysisChart
            title="Revenue Trend"
            data={revenueData}
            metric="Revenue"
            chartType="bar"
            yAxisLabel="Revenue ($)"
            color="#f59e0b"
            showExport={true}
            height={300}
          />
        )}

        {metrics.includes('expenses') && (
          <TrendAnalysisChart
            title="Operating Expenses Trend"
            data={expensesData}
            metric="Expenses"
            chartType="bar"
            yAxisLabel="Expenses ($)"
            color="#ef4444"
            showExport={true}
            height={300}
          />
        )}
      </div>
    </div>
  );
}
