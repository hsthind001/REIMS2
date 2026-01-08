/**
 * Document Completeness Dashboard
 *
 * Displays required document availability for a property and period.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, RefreshCw, XCircle } from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type DocumentCompletenessResults } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService, type FinancialPeriod } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';

export default function DocumentCompletenessDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [results, setResults] = useState<DocumentCompletenessResults | null>(null);
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
      const data = await forensicAuditService.getDocumentCompleteness(
        selectedPropertyId,
        selectedPeriodId
      );
      setResults(data);
    } catch (err: any) {
      console.error('Error loading document completeness results:', err);
      setError(err.response?.data?.detail || 'Failed to load document completeness results.');
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

  const documentChecklist = results
    ? [
        { label: 'Balance Sheet', present: results.has_balance_sheet },
        { label: 'Income Statement', present: results.has_income_statement },
        { label: 'Cash Flow Statement', present: results.has_cash_flow_statement },
        { label: 'Rent Roll', present: results.has_rent_roll },
        { label: 'Mortgage Statement', present: results.has_mortgage_statement },
      ]
    : [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Document Completeness</h1>
          <p className="text-gray-600 mt-1">Required forensic audit source documents</p>
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
              <div className="flex items-center gap-4">
                <FileText className="w-12 h-12 text-blue-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Completeness Score</h2>
                  <p className="text-gray-600">
                    {results.missing_documents.length === 0
                      ? 'All required documents are available.'
                      : `${results.missing_documents.length} document(s) missing.`}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="mb-2">
                  <TrafficLightIndicator status={results.status} size="lg" showLabel />
                </div>
                <div className="text-2xl font-semibold text-gray-900">
                  {results.completeness_percentage.toFixed(0)}%
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Document Checklist</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {documentChecklist.map((doc) => (
                <div
                  key={doc.label}
                  className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3"
                >
                  <span className="text-sm font-medium text-gray-900">{doc.label}</span>
                  {doc.present ? (
                    <span className="inline-flex items-center gap-1 text-green-600">
                      <CheckCircle2 className="w-4 h-4" />
                      Present
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-red-600">
                      <XCircle className="w-4 h-4" />
                      Missing
                    </span>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {results.missing_documents.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Missing Documents</h3>
              <ul className="list-disc list-inside text-sm text-gray-600">
                {results.missing_documents.map((doc) => (
                  <li key={doc}>{doc}</li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
