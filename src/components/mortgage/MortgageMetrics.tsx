/**
 * Mortgage Metrics Component
 * 
 * Displays DSCR, LTV, and debt service metrics with visual gauges
 */
import { useState, useEffect } from 'react';
import { mortgageService } from '../../lib/mortgage';
import type { DebtSummary } from '../../types/mortgage';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';

interface MortgageMetricsProps {
  propertyId: number;
  periodId: number;
}

export function MortgageMetrics({ propertyId, periodId }: MortgageMetricsProps) {
  const [debtSummary, setDebtSummary] = useState<DebtSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDebtSummary();
  }, [propertyId, periodId]);

  const loadDebtSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mortgageService.getDebtSummary(propertyId, periodId);
      setDebtSummary(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load debt summary');
      console.error('Failed to load debt summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value?: number) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercentage = (value?: number) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(2)}%`;
  };

  const getDSCRStatus = (dscr?: number) => {
    if (!dscr) return { status: 'unknown', color: 'gray', icon: null };
    if (dscr >= 1.25) return { status: 'healthy', color: 'green', icon: CheckCircle };
    if (dscr >= 1.10) return { status: 'warning', color: 'yellow', icon: AlertTriangle };
    return { status: 'critical', color: 'red', icon: AlertTriangle };
  };

  const getLTVStatus = (ltv?: number) => {
    if (!ltv) return { status: 'unknown', color: 'gray' };
    if (ltv <= 0.80) return { status: 'compliant', color: 'green' };
    if (ltv <= 0.90) return { status: 'warning', color: 'yellow' };
    return { status: 'breach', color: 'red' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading mortgage metrics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!debtSummary) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-8 text-center">
        <p className="text-gray-600">No mortgage data available for this period.</p>
      </div>
    );
  }

  const dscrStatus = getDSCRStatus(debtSummary.dscr);
  const ltvStatus = getLTVStatus(debtSummary.ltv);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* DSCR Gauge */}
      <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-700">DSCR</h3>
          {dscrStatus.icon && (
            <dscrStatus.icon className={`h-5 w-5 text-${dscrStatus.color}-600`} />
          )}
        </div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {debtSummary.dscr ? debtSummary.dscr.toFixed(2) : 'N/A'}
        </div>
        <div className="flex items-center space-x-2">
          <div className={`flex-1 h-2 rounded-full bg-${dscrStatus.color}-100`}>
            <div
              className={`h-2 rounded-full bg-${dscrStatus.color}-600`}
              style={{
                width: debtSummary.dscr
                  ? `${Math.min(100, (debtSummary.dscr / 2.0) * 100)}%`
                  : '0%'
              }}
            />
          </div>
          <span className={`text-xs font-medium text-${dscrStatus.color}-600`}>
            {dscrStatus.status}
          </span>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Threshold: 1.20
        </div>
      </div>

      {/* LTV Gauge */}
      <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-700">LTV Ratio</h3>
          {ltvStatus.status === 'compliant' ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : ltvStatus.status === 'warning' ? (
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-red-600" />
          )}
        </div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {debtSummary.ltv ? formatPercentage(debtSummary.ltv * 100) : 'N/A'}
        </div>
        <div className="flex items-center space-x-2">
          <div className={`flex-1 h-2 rounded-full bg-${ltvStatus.color}-100`}>
            <div
              className={`h-2 rounded-full bg-${ltvStatus.color}-600`}
              style={{
                width: debtSummary.ltv ? `${Math.min(100, debtSummary.ltv * 100)}%` : '0%'
              }}
            />
          </div>
          <span className={`text-xs font-medium text-${ltvStatus.color}-600`}>
            {ltvStatus.status}
          </span>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Max: 80%
        </div>
      </div>

      {/* Total Debt Service */}
      <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-4">Annual Debt Service</h3>
        <div className="text-2xl font-bold text-gray-900 mb-2">
          {formatCurrency(debtSummary.total_annual_debt_service)}
        </div>
        <div className="text-sm text-gray-500">
          Monthly: {formatCurrency(debtSummary.total_monthly_debt_service)}
        </div>
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            {debtSummary.mortgage_count} mortgage{debtSummary.mortgage_count !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Total Mortgage Debt */}
      <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-4">Total Mortgage Debt</h3>
        <div className="text-2xl font-bold text-gray-900 mb-2">
          {formatCurrency(debtSummary.total_mortgage_debt)}
        </div>
        {debtSummary.weighted_avg_interest_rate && (
          <div className="text-sm text-gray-500">
            Avg Rate: {formatPercentage(debtSummary.weighted_avg_interest_rate)}
          </div>
        )}
        {debtSummary.debt_yield && (
          <div className="mt-2 text-sm text-gray-500">
            Debt Yield: {formatPercentage(debtSummary.debt_yield)}
          </div>
        )}
      </div>

      {/* Additional Metrics Row */}
      {(debtSummary.interest_coverage_ratio || debtSummary.break_even_occupancy) && (
        <div className="col-span-full grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {debtSummary.interest_coverage_ratio && (
            <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Interest Coverage Ratio</h3>
              <div className="text-2xl font-bold text-gray-900">
                {debtSummary.interest_coverage_ratio.toFixed(2)}x
              </div>
            </div>
          )}
          {debtSummary.break_even_occupancy && (
            <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Break-Even Occupancy</h3>
              <div className="text-2xl font-bold text-gray-900">
                {formatPercentage(debtSummary.break_even_occupancy)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


