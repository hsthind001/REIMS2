/**
 * Mortgage Trends Component
 * 
 * Displays DSCR and LTV trends over time with charts
 */
import { useState, useEffect } from 'react';
import { mortgageService } from '../../lib/mortgage';
import type { DSCRHistory, LTVHistory } from '../../types/mortgage';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';

interface MortgageTrendsProps {
  propertyId: number;
}

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];

export function MortgageTrends({ propertyId }: MortgageTrendsProps) {
  const [dscrHistory, setDscrHistory] = useState<DSCRHistory | null>(null);
  const [ltvHistory, setLtvHistory] = useState<LTVHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dscr' | 'ltv' | 'principal' | 'interest'>('dscr');

  useEffect(() => {
    loadTrends();
  }, [propertyId]);

  const loadTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dscr, ltv] = await Promise.all([
        mortgageService.getDSCRHistory(propertyId, 12),
        mortgageService.getLTVHistory(propertyId, 12)
      ]);
      setDscrHistory(dscr);
      setLtvHistory(ltv);
    } catch (err: any) {
      setError(err.message || 'Failed to load trends');
      console.error('Failed to load trends:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading trends...</span>
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

  // Prepare chart data
  const dscrChartData = dscrHistory?.history.map(item => ({
    period: new Date(item.period).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
    dscr: item.dscr,
    status: item.status,
    noi: item.noi,
    debtService: item.total_debt_service
  })) || [];

  const ltvChartData = ltvHistory?.history.map(item => ({
    period: new Date(item.period).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
    ltv: item.ltv ? item.ltv * 100 : null,
    mortgageDebt: item.mortgage_debt,
    propertyValue: item.property_value
  })) || [];

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('dscr')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'dscr'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            DSCR Trend
          </button>
          <button
            onClick={() => setActiveTab('ltv')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'ltv'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            LTV Trend
          </button>
        </nav>
      </div>

      {/* DSCR Chart */}
      {activeTab === 'dscr' && dscrChartData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Debt Service Coverage Ratio (DSCR)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dscrChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip
                formatter={(value: any) => [value.toFixed(2), 'DSCR']}
                labelFormatter={(label) => `Period: ${label}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="dscr"
                stroke="#3b82f6"
                strokeWidth={2}
                name="DSCR"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey={() => 1.20}
                stroke="#ef4444"
                strokeWidth={1}
                strokeDasharray="5 5"
                name="Threshold (1.20)"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-sm">
              <span className="text-gray-500">Current DSCR: </span>
              <span className="font-semibold">
                {dscrChartData[dscrChartData.length - 1]?.dscr.toFixed(2)}
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Status: </span>
              <span className={`font-semibold ${
                dscrChartData[dscrChartData.length - 1]?.dscr >= 1.20
                  ? 'text-green-600'
                  : dscrChartData[dscrChartData.length - 1]?.dscr >= 1.10
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}>
                {dscrChartData[dscrChartData.length - 1]?.status || 'Unknown'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* LTV Chart */}
      {activeTab === 'ltv' && ltvChartData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Loan-to-Value Ratio (LTV)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={ltvChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip
                formatter={(value: any) => [`${value?.toFixed(2)}%`, 'LTV']}
                labelFormatter={(label) => `Period: ${label}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="ltv"
                stroke="#10b981"
                strokeWidth={2}
                name="LTV %"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey={() => 80}
                stroke="#ef4444"
                strokeWidth={1}
                strokeDasharray="5 5"
                name="Max (80%)"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-sm">
              <span className="text-gray-500">Current LTV: </span>
              <span className="font-semibold">
                {ltvChartData[ltvChartData.length - 1]?.ltv?.toFixed(2)}%
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Mortgage Debt: </span>
              <span className="font-semibold">
                {new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'USD',
                  minimumFractionDigits: 0
                }).format(ltvChartData[ltvChartData.length - 1]?.mortgageDebt || 0)}
              </span>
            </div>
          </div>
        </div>
      )}

      {(!dscrChartData.length && !ltvChartData.length) && (
        <div className="bg-gray-50 border border-gray-200 rounded p-8 text-center">
          <p className="text-gray-600">No trend data available for this property.</p>
        </div>
      )}
    </div>
  );
}


