/**
 * Reconciliation Results Dashboard
 *
 * Displays all 9 cross-document reconciliation results with pass/fail status
 */

import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  GitCompare,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  FileText,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type CrossDocumentReconciliationResults, type ReconciliationResult } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';

export default function ReconciliationResultsDashboard() {
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
  const [results, setResults] = useState<CrossDocumentReconciliationResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

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
      const data = await forensicAuditService.getReconciliations(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading reconciliations:', err);
      setError(err.response?.data?.detail || 'Failed to load reconciliation results. Run audit first.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'WARNING':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case 'FAIL':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return null;
    }
  };

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.hash = 'forensic-audit-dashboard';
  };

  const buildSummary = (data: CrossDocumentReconciliationResults | null) => {
    if (!data) return null;
    const total =
      data.summary?.total_reconciliations ??
      data.total_reconciliations ??
      data.reconciliations?.length ??
      0;
    const passed = data.summary?.passed ?? data.passed ?? 0;
    const failed = data.summary?.failed ?? data.failed ?? 0;
    const warnings = data.summary?.warnings ?? data.warnings ?? 0;
    const passRate = data.summary?.pass_rate ?? data.pass_rate;
    const passRatePct =
      data.summary?.pass_rate_pct ??
      (passRate != null
        ? passRate > 1
          ? passRate
          : passRate * 100
        : total > 0
          ? (passed / total) * 100
          : 0);
    const criticalFailures =
      data.summary?.critical_failures ??
      (data.reconciliations
        ? data.reconciliations.filter(
            (recon) => recon.status === 'FAIL' && recon.is_material
          ).length
        : 0);
    return {
      total_reconciliations: total,
      passed,
      failed,
      warnings,
      pass_rate: passRate,
      pass_rate_pct: passRatePct,
      critical_failures: criticalFailures,
    };
  };

  const summary = buildSummary(results);
  const passRatePct = summary?.pass_rate_pct ?? 0;
  const overallStatus =
    results?.overall_status ||
    (summary
      ? summary.failed > 0
        ? 'RED'
        : summary.warnings > 0
          ? 'YELLOW'
          : 'GREEN'
      : 'GREEN');

  const renderReconciliationCard = (recon: ReconciliationResult, index: number) => {
    const isExpanded = expandedIndex === index;

    return (
      <Card key={index} className="overflow-hidden">
        <div
          className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => setExpandedIndex(isExpanded ? null : index)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded">
                  {recon.rule_code}
                </span>
                {getStatusIcon(recon.status)}
                <span className={`font-semibold ${
                  recon.status === 'PASS' ? 'text-green-700' :
                  recon.status === 'WARNING' ? 'text-yellow-700' :
                  'text-red-700'
                }`}>
                  {recon.status}
                </span>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1">{recon.reconciliation_type}</h4>
              <div className="text-sm text-gray-600">
                {recon.source_document} → {recon.target_document}
              </div>
            </div>
            <div className="text-right ml-4">
              <div className="text-xs text-gray-500 mb-1">Difference</div>
              <div className={`text-lg font-bold ${
                Math.abs(recon.difference) <= recon.materiality_threshold
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}>
                {formatCurrency(Math.abs(recon.difference))}
              </div>
            </div>
          </div>

          {isExpanded && (
            <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-600 mb-1">Source Value</div>
                  <div className="font-semibold text-gray-900">
                    {formatCurrency(recon.source_value)}
                  </div>
                  <div className="text-xs text-gray-500">{recon.source_document}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-600 mb-1">Target Value</div>
                  <div className="font-semibold text-gray-900">
                    {formatCurrency(recon.target_value)}
                  </div>
                  <div className="text-xs text-gray-500">{recon.target_document}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-600 mb-1">Materiality Threshold</div>
                  <div className="font-semibold text-gray-900">
                    {formatCurrency(recon.materiality_threshold)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-600 mb-1">Material Difference?</div>
                  <div className={`font-semibold ${recon.is_material ? 'text-red-600' : 'text-green-600'}`}>
                    {recon.is_material ? 'YES' : 'NO'}
                  </div>
                </div>
              </div>

              {recon.intermediate_values && Object.keys(recon.intermediate_values).length > 0 && (
                <div>
                  <div className="text-xs text-gray-600 mb-2">Intermediate Values:</div>
                  <div className="bg-gray-50 p-3 rounded space-y-1">
                    {Object.entries(recon.intermediate_values).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700">{key}:</span>
                        <span className="font-medium">{formatCurrency(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-blue-50 p-3 rounded">
                <div className="text-xs font-semibold text-blue-900 mb-1">Explanation:</div>
                <p className="text-sm text-blue-800">{recon.explanation}</p>
              </div>

              {recon.recommendation && (
                <div className="bg-yellow-50 p-3 rounded">
                  <div className="text-xs font-semibold text-yellow-900 mb-1">Recommendation:</div>
                  <p className="text-sm text-yellow-800">{recon.recommendation}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
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
            <h1 className="text-3xl font-bold text-gray-900">Cross-Document Reconciliations</h1>
            <p className="text-gray-600 mt-1">
              {results 
                ? `${results.total_reconciliations} reconciliation rules across 5 financial statements`
                : 'Cross-document reconciliation rules'}
            </p>
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
          {/* Summary Card */}
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <GitCompare className="w-12 h-12 text-indigo-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Reconciliation Summary</h2>
                  <p className="text-gray-600">Overall pass rate across all reconciliations</p>
                </div>
              </div>
              <div className="text-right">
                <div className="mb-2">
                  <TrafficLightIndicator status={overallStatus as any} size="lg" showLabel />
                </div>
                <div className="text-lg font-semibold text-gray-900">
                  Pass Rate: {passRatePct.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 mt-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">{summary?.passed ?? 0}</div>
                <div className="text-sm text-gray-600">Passed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-yellow-600">{summary?.warnings ?? 0}</div>
                <div className="text-sm text-gray-600">Warnings</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-600">{summary?.failed ?? 0}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900">{summary?.total_reconciliations ?? 0}</div>
                <div className="text-sm text-gray-600">Total</div>
              </div>
            </div>

            {(summary?.critical_failures ?? 0) > 0 && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="font-semibold">
                    {summary?.critical_failures ?? 0} critical failure(s) detected
                  </span>
                </div>
              </div>
            )}
          </Card>

          {/* Reconciliation Cards */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Reconciliation Details
              <span className="text-sm font-normal text-gray-600 ml-2">
                (Click to expand for details)
              </span>
            </h2>
            <div className="space-y-3">
              {results.reconciliations.map((recon, index) => renderReconciliationCard(recon, index))}
            </div>
          </div>
        </>
      )}

      {/* No Data State */}
      {!loading && !results && !error && selectedPropertyId && selectedPeriodId && (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Reconciliation Data Available</h3>
          <p className="text-gray-600">
            Run a forensic audit from the main dashboard to generate reconciliation results.
          </p>
        </div>
      )}
    </div>
  );
}
