/**
 * Mathematical Integrity Dashboard
 *
 * Shows internal calculation checks for core financial documents.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { Card, Button } from '../components/design-system';
import {
  forensicAuditService,
  type MathIntegrityResults,
} from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService, type FinancialPeriod } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';

export default function MathIntegrityDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [results, setResults] = useState<MathIntegrityResults | null>(null);
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
      const data = await forensicAuditService.getMathIntegrity(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading mathematical integrity results:', err);
      setError(err.response?.data?.detail || 'Failed to load mathematical integrity results.');
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Mathematical Integrity</h1>
          <p className="text-gray-600 mt-1">Internal calculation checks across statements</p>
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

      {!loading && results && (
        <>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Overall Status</h2>
                <p className="text-gray-600">
                  {results.passed} of {results.total_checks} checks passed
                </p>
                {results.missing_documents.length > 0 && (
                  <p className="text-sm text-yellow-700 mt-1">
                    Missing documents: {results.missing_documents.join(', ')}
                  </p>
                )}
              </div>
              <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {results.documents.map((doc) => (
              <Card key={doc.document_type} className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">
                      {doc.document_type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </div>
                    <div className="text-xs text-gray-500">
                      {doc.passed}/{doc.total_checks} passed
                    </div>
                  </div>
                  <TrafficLightIndicator status={doc.overall_status} size="sm" />
                </div>
                {doc.missing && (
                  <div className="text-xs text-yellow-700 mt-2">Missing document</div>
                )}
              </Card>
            ))}
          </div>

          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Checks</h3>
            <div className="divide-y divide-gray-200">
              {results.checks.map((check) => (
                <div key={`${check.document_type}-${check.rule_name}`} className="py-3 flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{check.rule_name}</div>
                    <div className="text-xs text-gray-500">
                      {check.document_type.replace(/_/g, ' ')} · {check.rule_description || 'Calculation check'}
                    </div>
                    {check.error_message && (
                      <div className="text-xs text-red-600 mt-1">{check.error_message}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {check.passed ? (
                      <span className="inline-flex items-center gap-1 text-green-600">
                        <CheckCircle2 className="w-4 h-4" />
                        Pass
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-red-600">
                        <XCircle className="w-4 h-4" />
                        Fail
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
