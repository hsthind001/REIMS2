/**
 * Reconciliation Rules Panel
 *
 * Displays calculated rule evaluations for a property/period.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, Info, RefreshCw, XCircle } from 'lucide-react';
import { Card, Button } from '../design-system';
import {
  forensicReconciliationService,
  type CalculatedRuleEvaluationResponse,
  type CalculatedRuleEvaluation
} from '../../lib/forensic_reconciliation';

interface ReconciliationRulesPanelProps {
  propertyId: number;
  periodId: number;
}

const statusStyles: Record<string, string> = {
  PASS: 'bg-green-100 text-green-800',
  FAIL: 'bg-red-100 text-red-800',
  SKIPPED: 'bg-gray-100 text-gray-700'
};

const severityStyles: Record<string, string> = {
  critical: 'text-red-700',
  high: 'text-orange-700',
  medium: 'text-yellow-700',
  low: 'text-blue-700'
};

export default function ReconciliationRulesPanel({
  propertyId,
  periodId
}: ReconciliationRulesPanelProps) {
  const [data, setData] = useState<CalculatedRuleEvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRules = async () => {
    if (!propertyId || !periodId) return;

    try {
      setLoading(true);
      setError(null);
      const response = await forensicReconciliationService.evaluateCalculatedRules(propertyId, periodId);
      setData(response);
    } catch (err: any) {
      console.error('Failed to load calculated rules:', err);
      setError(err.response?.data?.detail || 'Failed to load calculated rule evaluations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, [propertyId, periodId]);

  const formatValue = (value?: number | null) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const renderStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'FAIL':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Info className="w-4 h-4 text-gray-500" />;
    }
  };

  const rules = data?.rules || [];

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Calculated Rules</h3>
            <p className="text-sm text-gray-600">Cross-document tieouts and statement equations</p>
          </div>
          <Button
            variant="info"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={loadRules}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {error && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        </Card>
      )}

      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-3 rounded bg-gray-50">
            <p className="text-xs text-gray-600">Total</p>
            <p className="text-2xl font-semibold text-gray-900">{data?.total ?? 0}</p>
          </div>
          <div className="p-3 rounded bg-green-50">
            <p className="text-xs text-green-700">Passed</p>
            <p className="text-2xl font-semibold text-green-900">{data?.passed ?? 0}</p>
          </div>
          <div className="p-3 rounded bg-red-50">
            <p className="text-xs text-red-700">Failed</p>
            <p className="text-2xl font-semibold text-red-900">{data?.failed ?? 0}</p>
          </div>
          <div className="p-3 rounded bg-gray-100">
            <p className="text-xs text-gray-600">Skipped</p>
            <p className="text-2xl font-semibold text-gray-900">{data?.skipped ?? 0}</p>
          </div>
        </div>
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-4 py-3 text-gray-600 font-medium">Rule</th>
                <th className="px-4 py-3 text-gray-600 font-medium">Status</th>
                <th className="px-4 py-3 text-gray-600 font-medium">Expected</th>
                <th className="px-4 py-3 text-gray-600 font-medium">Actual</th>
                <th className="px-4 py-3 text-gray-600 font-medium">Diff</th>
                <th className="px-4 py-3 text-gray-600 font-medium">Tolerance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rules.map((rule: CalculatedRuleEvaluation) => (
                <tr key={rule.rule_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{rule.rule_name}</div>
                    <div className="text-xs text-gray-500">{rule.rule_id}</div>
                    {rule.formula && (
                      <div className="text-xs text-gray-400 mt-1 font-mono">{rule.formula}</div>
                    )}
                    {rule.description && (
                      <div className="text-xs text-gray-500 mt-1">{rule.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {renderStatusIcon(rule.status)}
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${statusStyles[rule.status] || 'bg-gray-100 text-gray-700'}`}>
                        {rule.status}
                      </span>
                    </div>
                    <div className={`text-xs mt-1 ${severityStyles[rule.severity] || 'text-gray-500'}`}>
                      {rule.severity.toUpperCase()}
                    </div>
                    {rule.message && (
                      <div className="text-xs text-gray-500 mt-1">{rule.message}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{formatValue(rule.expected_value)}</td>
                  <td className="px-4 py-3 text-gray-700">{formatValue(rule.actual_value)}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {rule.difference !== null && rule.difference !== undefined
                      ? formatValue(rule.difference)
                      : 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    <div>{rule.tolerance_absolute != null ? formatValue(rule.tolerance_absolute) : 'N/A'}</div>
                    <div className="text-xs">
                      {rule.tolerance_percent != null ? `${rule.tolerance_percent.toFixed(2)}%` : 'N/A'}
                    </div>
                  </td>
                </tr>
              ))}
              {loading && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                    Loading calculated rules...
                  </td>
                </tr>
              )}
              {!loading && rules.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                    No calculated rules available. Seed rules to begin evaluation.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
