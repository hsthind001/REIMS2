/**
 * Covenant Compliance Dashboard
 *
 * Displays DSCR, LTV, Interest Coverage Ratio, and liquidity ratios
 * with covenant thresholds and breach alerts
 */

import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Shield,
  RefreshCw,
  Droplet,
  Bell,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type CovenantComplianceResults } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import TrendIndicator from '../components/forensic-audit/TrendIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';

export default function CovenantComplianceDashboard() {
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
  const [results, setResults] = useState<CovenantComplianceResults | null>(null);
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
      const data = await forensicAuditService.getCovenantCompliance(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading covenant compliance:', err);
      setError(err.response?.data?.detail || 'Failed to load covenant compliance. Run audit first.');
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

  const renderGauge = (
    value: number,
    covenant: number,
    label: string,
    isInverted: boolean = false // true for LTV (lower is better)
  ) => {
    const percentage = isInverted
      ? Math.min((value / covenant) * 100, 100)
      : Math.min((value / covenant) * 100, 100);

    const getColor = () => {
      if (isInverted) {
        // For LTV: lower is better
        if (value <= covenant * 0.65) return 'bg-green-500';
        if (value <= covenant * 0.75) return 'bg-yellow-500';
        return 'bg-red-500';
      } else {
        // For DSCR/ICR: higher is better
        if (value >= covenant * 1.2) return 'bg-green-500';
        if (value >= covenant) return 'bg-yellow-500';
        return 'bg-red-500';
      }
    };

    return (
      <div className="space-y-3">
        <div className="flex items-baseline justify-between">
          <span className="text-3xl font-bold text-gray-900">
            {isInverted ? `${value.toFixed(1)}%` : `${value.toFixed(2)}x`}
          </span>
          <span className="text-sm text-gray-600">
            Covenant: {isInverted ? `≤${covenant.toFixed(0)}%` : `≥${covenant.toFixed(2)}x`}
          </span>
        </div>
        <div className="relative">
          <div className="h-8 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${getColor()} transition-all duration-500`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <div
            className="absolute top-0 h-8 w-1 bg-gray-800"
            style={{ left: `${isInverted ? 100 : (covenant / value) * 100}%` }}
            title="Covenant Threshold"
          />
        </div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    );
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
            <h1 className="text-3xl font-bold text-gray-900">Covenant Compliance</h1>
            <p className="text-gray-600 mt-1">Lender covenant monitoring and breach alerts</p>
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
                <Shield className="w-12 h-12 text-blue-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Covenant Status</h2>
                  <p className="text-gray-600">Overall lender covenant compliance</p>
                </div>
              </div>
              <div className="text-right">
                <div className="mb-2">
                  <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
                </div>
                {results.lender_notification_required && (
                  <div className="flex items-center gap-2 text-red-600 font-semibold">
                    <Bell className="w-4 h-4" />
                    <span>Lender Notification Required</span>
                  </div>
                )}
                {results.any_breaches && (
                  <div className="text-red-600 font-semibold">Covenant Breach Detected</div>
                )}
              </div>
            </div>
          </Card>

          {/* Summary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              title="DSCR Status"
              value={results.tests.dscr.status}
              subtitle={`${results.tests.dscr.dscr.toFixed(2)}x`}
              status={results.tests.dscr.status as any}
              trend={results.tests.dscr.trend}
              icon={TrendingUp}
              iconColor="text-blue-600"
            />
            <MetricCard
              title="LTV Status"
              value={results.tests.ltv.status}
              subtitle={`${results.tests.ltv.ltv.toFixed(1)}%`}
              status={results.tests.ltv.status as any}
              trend={results.tests.ltv.trend}
              icon={DollarSign}
              iconColor="text-green-600"
            />
            <MetricCard
              title="ICR Status"
              value={results.tests.interest_coverage.status}
              subtitle={`${results.tests.interest_coverage.icr.toFixed(2)}x`}
              status={results.tests.interest_coverage.status as any}
              icon={Shield}
              iconColor="text-purple-600"
            />
            <MetricCard
              title="Liquidity Status"
              value={results.tests.liquidity.status}
              subtitle={`Current: ${results.tests.liquidity.current_ratio.toFixed(2)}x`}
              status={results.tests.liquidity.status as any}
              icon={Droplet}
              iconColor="text-teal-600"
            />
          </div>

          {/* DSCR Analysis */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-blue-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Debt Service Coverage Ratio (DSCR)</h3>
                  <p className="text-sm text-gray-600">Net Operating Income / Annual Debt Service</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <TrendIndicator
                  trend={results.tests.dscr.trend || 'STABLE'}
                  value={results.tests.dscr.dscr}
                  previousValue={results.tests.dscr.prior_period_dscr}
                  showLabel
                />
                <TrafficLightIndicator status={results.tests.dscr.status as any} size="md" showLabel />
              </div>
            </div>

            {renderGauge(
              results.tests.dscr.dscr,
              results.tests.dscr.covenant_threshold,
              'Higher is better - indicates ability to service debt'
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              <div>
                <div className="text-sm text-gray-600">NOI</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.dscr.noi)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Annual Debt Service</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.dscr.annual_debt_service)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Cushion</div>
                <div className={`text-xl font-bold ${
                  results.tests.dscr.cushion > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {results.tests.dscr.cushion.toFixed(2)}x ({results.tests.dscr.cushion_pct.toFixed(1)}%)
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg mt-4">
              <p className="text-sm text-gray-700">{results.tests.dscr.explanation}</p>
            </div>
          </Card>

          {/* LTV Analysis */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <DollarSign className="w-6 h-6 text-green-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Loan-to-Value Ratio (LTV)</h3>
                  <p className="text-sm text-gray-600">Mortgage Balance / Property Value</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <TrendIndicator
                  trend={results.tests.ltv.trend || 'STABLE'}
                  value={results.tests.ltv.ltv}
                  previousValue={results.tests.ltv.prior_period_ltv}
                  showLabel
                />
                <TrafficLightIndicator status={results.tests.ltv.status as any} size="md" showLabel />
              </div>
            </div>

            {renderGauge(
              results.tests.ltv.ltv,
              results.tests.ltv.covenant_threshold,
              'Lower is better - indicates equity cushion',
              true
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              <div>
                <div className="text-sm text-gray-600">Mortgage Balance</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.ltv.mortgage_balance)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Property Value</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.ltv.property_value)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Cushion</div>
                <div className={`text-xl font-bold ${
                  results.tests.ltv.cushion_pct > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {results.tests.ltv.cushion_pct.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg mt-4">
              <p className="text-sm text-gray-700">{results.tests.ltv.explanation}</p>
            </div>
          </Card>

          {/* Interest Coverage Ratio */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-purple-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Interest Coverage Ratio (ICR)</h3>
                  <p className="text-sm text-gray-600">Net Operating Income / Interest Expense</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.tests.interest_coverage.status as any} size="md" showLabel />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <div className="text-sm text-gray-600">Current ICR</div>
                <div className="text-3xl font-bold text-gray-900">
                  {results.tests.interest_coverage.icr.toFixed(2)}x
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">NOI</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.interest_coverage.noi)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Interest Expense</div>
                <div className="text-xl font-bold text-gray-900">
                  {formatCurrency(results.tests.interest_coverage.interest_expense)}
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg mt-4">
              <p className="text-sm text-gray-700">{results.tests.interest_coverage.explanation}</p>
            </div>
          </Card>

          {/* Liquidity Ratios */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Droplet className="w-6 h-6 text-teal-600" />
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Liquidity Ratios</h3>
                  <p className="text-sm text-gray-600">Current and quick ratio analysis</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.tests.liquidity.status as any} size="md" showLabel />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="text-sm text-gray-600 mb-2">Current Ratio</div>
                <div className="text-3xl font-bold text-gray-900 mb-1">
                  {results.tests.liquidity.current_ratio.toFixed(2)}x
                </div>
                <div className="text-xs text-gray-500">Target: ≥1.5x</div>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Current Assets:</span>
                    <span className="font-medium">{formatCurrency(results.tests.liquidity.current_assets)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Current Liabilities:</span>
                    <span className="font-medium">{formatCurrency(results.tests.liquidity.current_liabilities)}</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-sm text-gray-600 mb-2">Quick Ratio</div>
                <div className="text-3xl font-bold text-gray-900 mb-1">
                  {results.tests.liquidity.quick_ratio.toFixed(2)}x
                </div>
                <div className="text-xs text-gray-500">Target: ≥1.0x</div>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Quick Assets:</span>
                    <span className="font-medium">{formatCurrency(results.tests.liquidity.quick_assets)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Current Liabilities:</span>
                    <span className="font-medium">{formatCurrency(results.tests.liquidity.current_liabilities)}</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* No Data State */}
      {!loading && !results && !error && selectedPropertyId && selectedPeriodId && (
        <div className="text-center py-12">
          <Shield className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Covenant Data Available</h3>
          <p className="text-gray-600">
            Run a forensic audit from the main dashboard to generate covenant compliance results.
          </p>
        </div>
      )}
    </div>
  );
}
