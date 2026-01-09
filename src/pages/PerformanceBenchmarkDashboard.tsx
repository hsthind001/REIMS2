/**
 * Performance & Benchmarking Dashboard
 *
 * Phase 8 metrics: same-store growth, NOI margin, OpEx ratio, CapEx ratio.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, BarChart3, DollarSign, RefreshCw, TrendingUp, Percent } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Card, Button } from '../components/design-system';
import {
  forensicAuditService,
  type PerformanceBenchmarkResults,
  type PerformanceBenchmarkMetric,
} from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService, type FinancialPeriod } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';

const metricIconMap: Record<string, LucideIcon> = {
  same_store_growth: TrendingUp,
  noi_margin: Percent,
  operating_expense_ratio: BarChart3,
  capex_ratio: DollarSign,
};

export default function PerformanceBenchmarkDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [results, setResults] = useState<PerformanceBenchmarkResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedPropertyId) {
      loadPeriods(selectedPropertyId);
    } else {
      setPeriods([]);
      setSelectedPeriodId('');
    }
  }, [selectedPropertyId]);

  useEffect(() => {
    if (selectedPropertyId && selectedPeriodId) {
      loadResults();
    }
  }, [selectedPropertyId, selectedPeriodId]);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0) {
        setSelectedPropertyId(String(data[0].id));
      }
    } catch (err) {
      console.error('Error loading properties:', err);
      setError('Failed to load properties');
    }
  };

  const loadPeriods = async (propertyId: string) => {
    try {
      const data = await financialPeriodsService.getPeriods(Number(propertyId));
      setPeriods(data);
      if (data.length > 0) {
        setSelectedPeriodId(String(data[0].id));
      } else {
        setSelectedPeriodId('');
      }
    } catch (err) {
      console.error('Error loading periods:', err);
      setError('Failed to load periods');
    }
  };

  const loadResults = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await forensicAuditService.getPerformanceBenchmark(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading performance benchmarks:', err);
      setError(err.response?.data?.detail || 'Failed to load performance benchmarks.');
    } finally {
      setLoading(false);
    }
  };

  const formatPeriodLabel = (period: FinancialPeriod): string => {
    if (period.period_year && period.period_month) {
      return `${period.period_year}-${String(period.period_month).padStart(2, '0')}`;
    }
    return `Period ${period.id}`;
  };

  const getPropertyLabel = (property: Property): string => {
    return property.property_name || property.property_code || `Property ${property.id}`;
  };

  const formatMetricValue = (metric: PerformanceBenchmarkMetric): string => {
    if (metric.current_value == null) return 'N/A';
    if (metric.unit === '%') {
      return `${metric.current_value.toFixed(1)}%`;
    }
    if (metric.unit === 'x') {
      return `${metric.current_value.toFixed(2)}x`;
    }
    return metric.current_value.toFixed(2);
  };

  const getBenchmarkLabel = (metric: PerformanceBenchmarkMetric): string | undefined => {
    if (metric.benchmark_label) return metric.benchmark_label;
    if (metric.benchmark_low != null && metric.benchmark_high != null) {
      const unit = metric.unit || '';
      return `${metric.benchmark_low}-${metric.benchmark_high}${unit}`;
    }
    return undefined;
  };

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.hash = 'forensic-audit-dashboard';
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" icon={<ArrowLeft className="w-4 h-4" />} onClick={handleBack}>
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Performance & Benchmarking</h1>
            <p className="text-gray-600 mt-1">Phase 8 metrics vs market benchmarks</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <select
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select Property</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {getPropertyLabel(property)}
              </option>
            ))}
          </select>

          <select
            value={selectedPeriodId}
            onChange={(e) => setSelectedPeriodId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            disabled={!selectedPropertyId}
          >
            <option value="">Select Period</option>
            {periods.map((period) => (
              <option key={period.id} value={period.id}>
                {formatPeriodLabel(period)}
              </option>
            ))}
          </select>

          <Button
            onClick={loadResults}
            disabled={loading || !selectedPropertyId || !selectedPeriodId}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      )}

      {!loading && results && (
        <>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Overall Status</h2>
                <p className="text-gray-600">Benchmark comparison for {results.period_label}</p>
                {results.missing_inputs.length > 0 && (
                  <p className="text-sm text-yellow-700 mt-1">
                    Missing inputs: {results.missing_inputs.join(', ')}
                  </p>
                )}
              </div>
              <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {results.metrics.map((metric) => {
              const Icon = metricIconMap[metric.metric_key] || TrendingUp;
              const benchmark = getBenchmarkLabel(metric);

              return (
                <MetricCard
                  key={metric.metric_key}
                  title={metric.metric_name}
                  value={formatMetricValue(metric)}
                  subtitle={metric.description}
                  status={metric.status}
                  trend={metric.trend}
                  previousValue={metric.previous_value}
                  icon={Icon}
                  iconColor="text-blue-600"
                  target={benchmark}
                  targetLabel="Benchmark"
                />
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
