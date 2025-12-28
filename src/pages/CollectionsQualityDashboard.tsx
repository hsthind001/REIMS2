/**
 * Collections Quality Dashboard
 *
 * Displays revenue quality, DSO, cash conversion, and A/R aging
 */

import { useState, useEffect } from 'react';
import {
  DollarSign,
  TrendingUp,
  Clock,
  BarChart3,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type CollectionsQualityResults } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';
import HealthScoreGauge from '../components/forensic-audit/HealthScoreGauge';

export default function CollectionsQualityDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<any[]>([]);
  const [results, setResults] = useState<CollectionsQualityResults | null>(null);
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
    }
  };

  const loadPeriods = async (propertyId: string) => {
    try {
      const data = await financialPeriodsService.getPeriods(Number(propertyId));
      setPeriods(data);
      if (data.length > 0) {
        setSelectedPeriodId(String(data[0].id));
      }
    } catch (err) {
      console.error('Error loading periods:', err);
    }
  };

  const loadResults = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await forensicAuditService.getCollectionsQuality(selectedPropertyId, selectedPeriodId);
      setResults(data);
    } catch (err: any) {
      console.error('Error loading collections quality:', err);
      setError(err.response?.data?.detail || 'Failed to load collections quality analysis. Run audit first.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getARAgingColor = (days: string): string => {
    if (days.includes('0-30')) return 'bg-green-500';
    if (days.includes('31-60')) return 'bg-yellow-500';
    if (days.includes('61-90')) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Collections Quality Analysis</h1>
          <p className="text-gray-600 mt-1">Revenue quality, DSO, and A/R aging assessment</p>
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
                {property.name}
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
                {period.name}
              </option>
            ))}
          </select>

          <Button onClick={loadResults} disabled={loading || !selectedPropertyId || !selectedPeriodId}>
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
          {/* Overall Status */}
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <DollarSign className="w-12 h-12 text-green-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Overall Collections Quality</h2>
                  <p className="text-gray-600">Revenue quality and cash conversion assessment</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
            </div>
          </Card>

          {/* Revenue Quality Score */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Revenue Quality Score</h3>
                  <p className="text-sm text-gray-600">Composite collections health metric</p>
                </div>
              </div>

              <div className="flex items-center justify-center">
                <HealthScoreGauge
                  score={results.revenue_quality.quality_score}
                  size="lg"
                  showLabel
                />
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Total Revenue:</span>
                  <span className="font-bold text-gray-900">
                    {formatCurrency(results.revenue_quality.total_revenue)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Collectible Revenue:</span>
                  <span className="font-bold text-green-600">
                    {formatCurrency(results.revenue_quality.collectible_revenue)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">At-Risk Revenue:</span>
                  <span className="font-bold text-red-600">
                    {formatCurrency(results.revenue_quality.at_risk_revenue)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Collectible %:</span>
                  <span className="font-bold text-gray-900">
                    {results.revenue_quality.collectible_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </Card>

            {/* Days Sales Outstanding */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <Clock className="w-6 h-6 text-blue-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Days Sales Outstanding (DSO)</h3>
                  <p className="text-sm text-gray-600">Average collection period</p>
                </div>
              </div>

              <div className="text-center mb-6">
                <div className="text-5xl font-bold text-gray-900 mb-2">
                  {results.dso.current_dso.toFixed(0)}
                </div>
                <div className="text-gray-600">days</div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">Target DSO:</span>
                  <span className="font-bold text-gray-900">{results.dso.target_dso.toFixed(0)} days</span>
                </div>

                {results.dso.previous_dso !== null && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">Previous DSO:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900">
                        {results.dso.previous_dso.toFixed(0)} days
                      </span>
                      {results.dso.current_dso < results.dso.previous_dso ? (
                        <TrendingUp className="w-4 h-4 text-green-600 rotate-180" />
                      ) : (
                        <TrendingUp className="w-4 h-4 text-red-600" />
                      )}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">Status:</span>
                  <TrafficLightIndicator status={results.dso.dso_status} size="sm" showLabel />
                </div>
              </div>
            </Card>
          </div>

          {/* Cash Conversion Ratio */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <BarChart3 className="w-6 h-6 text-teal-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Cash Conversion Ratio</h3>
                <p className="text-sm text-gray-600">Cash collected vs. revenue recognized</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-2">Revenue Recognized</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(results.cash_conversion.revenue_recognized)}
                </div>
              </div>

              <div className="text-center">
                <div className="text-sm text-gray-600 mb-2">Cash Collected</div>
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(results.cash_conversion.cash_collected)}
                </div>
              </div>

              <div className="text-center">
                <div className="text-sm text-gray-600 mb-2">Conversion Ratio</div>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {results.cash_conversion.conversion_ratio.toFixed(1)}%
                </div>
                <TrafficLightIndicator
                  status={results.cash_conversion.conversion_status}
                  size="sm"
                  showLabel
                />
              </div>
            </div>

            <div className="mt-6">
              <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    results.cash_conversion.conversion_ratio >= 95
                      ? 'bg-green-500'
                      : results.cash_conversion.conversion_ratio >= 85
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(results.cash_conversion.conversion_ratio, 100)}%` }}
                />
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-600">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
          </Card>

          {/* A/R Aging Analysis */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Clock className="w-6 h-6 text-purple-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Accounts Receivable Aging</h3>
                <p className="text-sm text-gray-600">Distribution by aging bucket</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MetricCard
                  title="0-30 Days"
                  value={formatCurrency(results.ar_aging.current_0_30)}
                  subtitle={`${results.ar_aging.current_0_30_pct.toFixed(1)}% of total`}
                  status="GREEN"
                  icon={Clock}
                  iconColor="text-green-600"
                />
                <MetricCard
                  title="31-60 Days"
                  value={formatCurrency(results.ar_aging.days_31_60)}
                  subtitle={`${results.ar_aging.days_31_60_pct.toFixed(1)}% of total`}
                  status={results.ar_aging.days_31_60_pct > 25 ? 'YELLOW' : 'GREEN'}
                  icon={Clock}
                  iconColor="text-yellow-600"
                />
                <MetricCard
                  title="61-90 Days"
                  value={formatCurrency(results.ar_aging.days_61_90)}
                  subtitle={`${results.ar_aging.days_61_90_pct.toFixed(1)}% of total`}
                  status={results.ar_aging.days_61_90_pct > 15 ? 'RED' : results.ar_aging.days_61_90_pct > 10 ? 'YELLOW' : 'GREEN'}
                  icon={Clock}
                  iconColor="text-orange-600"
                />
                <MetricCard
                  title="90+ Days"
                  value={formatCurrency(results.ar_aging.over_90)}
                  subtitle={`${results.ar_aging.over_90_pct.toFixed(1)}% of total`}
                  status={results.ar_aging.over_90_pct > 10 ? 'RED' : results.ar_aging.over_90_pct > 5 ? 'YELLOW' : 'GREEN'}
                  icon={Clock}
                  iconColor="text-red-600"
                />
              </div>

              <div className="mt-6">
                <div className="text-sm font-medium text-gray-700 mb-3">Aging Distribution:</div>
                <div className="relative">
                  <div className="flex h-12 rounded-lg overflow-hidden">
                    <div
                      className="bg-green-500 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                      style={{ width: `${results.ar_aging.current_0_30_pct}%` }}
                    >
                      {results.ar_aging.current_0_30_pct > 10 && `${results.ar_aging.current_0_30_pct.toFixed(0)}%`}
                    </div>
                    <div
                      className="bg-yellow-500 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                      style={{ width: `${results.ar_aging.days_31_60_pct}%` }}
                    >
                      {results.ar_aging.days_31_60_pct > 10 && `${results.ar_aging.days_31_60_pct.toFixed(0)}%`}
                    </div>
                    <div
                      className="bg-orange-500 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                      style={{ width: `${results.ar_aging.days_61_90_pct}%` }}
                    >
                      {results.ar_aging.days_61_90_pct > 10 && `${results.ar_aging.days_61_90_pct.toFixed(0)}%`}
                    </div>
                    <div
                      className="bg-red-500 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                      style={{ width: `${results.ar_aging.over_90_pct}%` }}
                    >
                      {results.ar_aging.over_90_pct > 10 && `${results.ar_aging.over_90_pct.toFixed(0)}%`}
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <span className="text-gray-700 font-medium">Total A/R:</span>
                  <span className="text-2xl font-bold text-gray-900">
                    {formatCurrency(results.ar_aging.total_ar)}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Collections Efficiency */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-gray-900">Collections Rate</h3>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {results.efficiency.collection_rate.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">
                Of revenue collected on time
              </div>
              <div className="mt-4">
                <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full transition-all duration-500"
                    style={{ width: `${results.efficiency.collection_rate}%` }}
                  />
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <DollarSign className="w-5 h-5 text-green-600" />
                <h3 className="font-bold text-gray-900">Write-Off Rate</h3>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {results.efficiency.write_off_rate.toFixed(2)}%
              </div>
              <div className="text-sm text-gray-600">
                Of revenue written off
              </div>
              <div className="mt-4">
                <TrafficLightIndicator
                  status={results.efficiency.write_off_rate < 2 ? 'GREEN' : results.efficiency.write_off_rate < 5 ? 'YELLOW' : 'RED'}
                  size="sm"
                  showLabel
                />
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <BarChart3 className="w-5 h-5 text-purple-600" />
                <h3 className="font-bold text-gray-900">Recovery Rate</h3>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {results.efficiency.recovery_rate.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">
                Of overdue amounts recovered
              </div>
              <div className="mt-4">
                <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-purple-500 h-full transition-all duration-500"
                    style={{ width: `${results.efficiency.recovery_rate}%` }}
                  />
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
