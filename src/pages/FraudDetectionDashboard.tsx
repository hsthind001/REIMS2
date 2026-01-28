/**
 * Fraud Detection Dashboard
 *
 * Displays Benford's Law analysis, round number detection,
 * duplicate payments, and cash conversion ratio
 */

import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Shield,
  AlertTriangle,
  TrendingDown,
  Copy,
  DollarSign,
  RefreshCw,
  BarChart3,
  AlertCircle,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type FraudDetectionResults } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';

export default function FraudDetectionDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>(() => {
    const saved = localStorage.getItem('reims_forensic_property_id');
    return saved || '';
  });
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>(() => {
    const saved = localStorage.getItem('reims_forensic_period_id');
    return saved || '';
  });
  const [periods, setPeriods] = useState<any[]>([]);
  const [results, setResults] = useState<FraudDetectionResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist property selection to localStorage
  useEffect(() => {
    if (selectedPropertyId) {
      localStorage.setItem('reims_forensic_property_id', selectedPropertyId);
    }
  }, [selectedPropertyId]);

  // Persist period selection to localStorage
  useEffect(() => {
    if (selectedPeriodId) {
      localStorage.setItem('reims_forensic_period_id', selectedPeriodId);
    }
  }, [selectedPeriodId]);

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

      // Restore from localStorage if available
      const savedPropId = localStorage.getItem('reims_forensic_property_id');
      const savedPropExists = data.find(p => String(p.id) === savedPropId);

      if (savedPropExists) {
        setSelectedPropertyId(String(savedPropId));
      } else if (data.length > 0) {
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

      // Restore from localStorage if available
      const savedPeriodId = localStorage.getItem('reims_forensic_period_id');
      const savedPeriodExists = data.find(p => String(p.id) === savedPeriodId);

      if (savedPeriodExists) {
        setSelectedPeriodId(String(savedPeriodId));
      } else if (data.length > 0) {
        const latestCompletePeriod = data.find(p => p.is_complete);
        
        if (latestCompletePeriod) {
          setSelectedPeriodId(String(latestCompletePeriod.id));
        } else {
          setSelectedPeriodId(String(data[0].id));
        }
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
      const data = await forensicAuditService.getFraudDetection(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading fraud detection results:', err);
      setError(err.response?.data?.detail || 'Failed to load fraud detection results. Run audit first.');
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

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.hash = 'forensic-audit-dashboard';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" icon={<ArrowLeft className="w-4 h-4" />} onClick={handleBack}>
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Fraud Detection Analysis</h1>
            <p className="text-gray-600 mt-1">Statistical fraud detection using Big 5 methodologies</p>
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

          <Button
            onClick={loadResults}
            disabled={loading || !selectedPropertyId || !selectedPeriodId}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      )}

      {/* Main Content */}
      {!loading && results && (
        <>
          {/* Overall Status */}
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Shield className="w-12 h-12 text-purple-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Overall Fraud Risk</h2>
                  <p className="text-gray-600">Composite assessment from 4 fraud tests</p>
                </div>
              </div>
              <div className="text-right">
                <div className="mb-2">
                  <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
                </div>
                <div className="text-lg font-semibold text-gray-900">{results.fraud_risk_level}</div>
              </div>
            </div>
          </Card>

          {/* Summary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              title="Total Tests"
              value={results.summary.total_tests}
              subtitle="Fraud detection tests"
              icon={BarChart3}
              iconColor="text-blue-600"
            />
            <MetricCard
              title="Tests Passed"
              value={results.summary.tests_passed}
              subtitle="No fraud indicators"
              status="GREEN"
              icon={Shield}
              iconColor="text-green-600"
            />
            <MetricCard
              title="Warnings"
              value={results.summary.tests_warning}
              subtitle="Requires review"
              status={results.summary.tests_warning > 0 ? 'YELLOW' : 'GREEN'}
              icon={AlertCircle}
              iconColor="text-yellow-600"
            />
            <MetricCard
              title="Failed Tests"
              value={results.summary.tests_failed}
              subtitle="Fraud indicators detected"
              status={results.summary.tests_failed > 0 ? 'RED' : 'GREEN'}
              icon={AlertTriangle}
              iconColor="text-red-600"
            />
          </div>

          {/* Benford's Law Analysis */}
          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <BarChart3 className="w-6 h-6 text-indigo-600" />
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">Benford's Law Analysis</h3>
                    <p className="text-sm text-gray-600">First digit distribution chi-square test</p>
                  </div>
                </div>
                <TrafficLightIndicator status={results.tests.benfords_law.status} size="md" showLabel />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div>
                  <div className="text-sm text-gray-600">Chi-Square Statistic</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {results.tests.benfords_law.chi_square.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Critical Value (α=0.05)</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {results.tests.benfords_law.critical_value_005.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Sample Size</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {results.tests.benfords_law.sample_size.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-700">{results.tests.benfords_law.explanation}</p>
              </div>

              {/* Distribution Chart */}
              <div className="mt-6">
                <div className="text-sm font-medium text-gray-700 mb-3">First Digit Distribution</div>
                <div className="space-y-2">
                  {Object.entries(results.tests.benfords_law.expected_distribution).map(([digit, expected]) => {
                    const actual = results.tests.benfords_law.actual_distribution[Number(digit)] || 0;
                    const maxValue = Math.max(expected, actual);
                    return (
                      <div key={digit} className="flex items-center gap-3">
                        <div className="w-8 text-sm font-medium text-gray-700">{digit}</div>
                        <div className="flex-1 flex gap-2">
                          <div className="flex-1">
                            <div className="text-xs text-gray-600 mb-1">Expected: {expected.toFixed(1)}%</div>
                            <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                              <div
                                className="bg-blue-500 h-full"
                                style={{ width: `${(expected / maxValue) * 100}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex-1">
                            <div className="text-xs text-gray-600 mb-1">Actual: {actual.toFixed(1)}%</div>
                            <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                              <div
                                className="bg-green-500 h-full"
                                style={{ width: `${(actual / maxValue) * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>

          {/* Round Number Analysis */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <TrendingDown className="w-6 h-6 text-orange-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Round Number Detection</h3>
                  <p className="text-sm text-gray-600">Fabrication indicator - natural transactions are rarely round</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.tests.round_numbers.status} size="md" showLabel />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
              <div>
                <div className="text-sm text-gray-600">Total Transactions</div>
                <div className="text-2xl font-bold text-gray-900">
                  {results.tests.round_numbers.total_transactions.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Round Numbers</div>
                <div className="text-2xl font-bold text-gray-900">
                  {results.tests.round_numbers.round_number_count.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Percentage</div>
                <div className={`text-2xl font-bold ${
                  results.tests.round_numbers.round_number_pct > 10 ? 'text-red-600' :
                  results.tests.round_numbers.round_number_pct > 5 ? 'text-yellow-600' :
                  'text-green-600'
                }`}>
                  {results.tests.round_numbers.round_number_pct.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-700">{results.tests.round_numbers.explanation}</p>
            </div>
          </Card>

          {/* Duplicate Payments */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Copy className="w-6 h-6 text-red-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Duplicate Payment Detection</h3>
                  <p className="text-sm text-gray-600">Identical amount, vendor, and date combinations</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.tests.duplicate_payments.status} size="md" showLabel />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
              <div>
                <div className="text-sm text-gray-600">Duplicates Found</div>
                <div className={`text-2xl font-bold ${
                  results.tests.duplicate_payments.duplicates_found > 0 ? 'text-red-600' : 'text-green-600'
                }`}>
                  {results.tests.duplicate_payments.duplicates_found}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Total Duplicate Amount</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(results.tests.duplicate_payments.total_duplicate_amount)}
                </div>
              </div>
            </div>

            {results.tests.duplicate_payments.duplicate_pairs.length > 0 && (
              <div className="mt-4">
                <div className="text-sm font-medium text-gray-700 mb-2">Duplicate Pairs:</div>
                <div className="space-y-2">
                  {results.tests.duplicate_payments.duplicate_pairs.map((dup, idx) => (
                    <div key={idx} className="bg-red-50 p-3 rounded-lg border border-red-200">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-900">{dup.vendor}</div>
                          <div className="text-sm text-gray-600">{dup.description}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-gray-900">{formatCurrency(dup.amount ?? 0)}</div>
                          <div className="text-xs text-gray-600">{dup.date}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-gray-50 p-4 rounded-lg mt-4">
              <p className="text-sm text-gray-700">{results.tests.duplicate_payments.explanation}</p>
            </div>
          </Card>

          {/* Cash Conversion Ratio */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <DollarSign className="w-6 h-6 text-green-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Cash Conversion Ratio</h3>
                  <p className="text-sm text-gray-600">Cash from operations vs. net income alignment</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.tests.cash_conversion.status} size="md" showLabel />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
              <div>
                <div className="text-sm text-gray-600">Cash from Operations</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(results.tests.cash_conversion.cash_from_operations)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Net Income</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(results.tests.cash_conversion.net_income)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Conversion Ratio</div>
                <div className={`text-2xl font-bold ${
                  results.tests.cash_conversion.cash_conversion_ratio >= 0.9 ? 'text-green-600' :
                  results.tests.cash_conversion.cash_conversion_ratio >= 0.7 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {results.tests.cash_conversion.cash_conversion_ratio.toFixed(2)}x
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-700">{results.tests.cash_conversion.explanation}</p>
            </div>
          </Card>
        </>
      )}

      {/* No Data State */}
      {!loading && !results && !error && selectedPropertyId && selectedPeriodId && (
        <div className="text-center py-12">
          <Shield className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Fraud Detection Results</h3>
          <p className="text-gray-600">
            Run a forensic audit from the main dashboard to generate fraud detection results.
          </p>
        </div>
      )}
    </div>
  );
}
