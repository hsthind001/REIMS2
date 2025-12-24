/**
 * Reconciliation Diagnostics Component
 * 
 * Displays diagnostic information about reconciliation including:
 * - Discovered account codes
 * - Missing account warnings
 * - Suggested fixes
 * - Reconciliation statistics
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info, RefreshCw } from 'lucide-react';
import { Card } from '../design-system';
import { api } from '../../lib/api';

interface ReconciliationDiagnosticsProps {
  propertyId: number;
  periodId: number;
  onRefresh?: () => void;
}

interface DiagnosticData {
  property_id: number;
  period_id: number;
  data_availability: {
    [key: string]: {
      has_data: boolean;
      record_count: number;
      account_codes?: string[];
    };
  };
  discovered_accounts: {
    [key: string]: Array<{
      account_code: string;
      account_name: string;
      account_type?: string;
      occurrence_count: number;
    }>;
  };
  missing_accounts: {
    [key: string]: string[];
  };
  suggested_fixes: Array<{
    issue: string;
    suggestion: string;
    confidence: number;
    action: string;
    similar_accounts?: Array<{
      account_code: string;
      account_name: string;
      similarity_type: string;
      confidence: number;
    }>;
  }>;
  learned_patterns: Array<{
    pattern_name: string;
    source_document_type: string;
    target_document_type: string;
    source_account_code?: string;
    target_account_code?: string;
    relationship_type?: string;
    success_rate: number;
    average_confidence: number;
  }>;
  recommendations: string[];
}

export default function ReconciliationDiagnostics({
  propertyId,
  periodId,
  onRefresh
}: ReconciliationDiagnosticsProps) {
  const [diagnostics, setDiagnostics] = useState<DiagnosticData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['data_availability', 'recommendations']));

  useEffect(() => {
    if (propertyId && periodId) {
      loadDiagnostics();
    }
  }, [propertyId, periodId]);

  const loadDiagnostics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.get<DiagnosticData>(`/forensic-reconciliation/diagnostics/${propertyId}/${periodId}`);
      setDiagnostics(data);
    } catch (err: any) {
      console.error('Failed to load diagnostics:', err);
      setError(err.response?.data?.detail || 'Failed to load diagnostics');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Loading diagnostics...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 text-red-600">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
          <button
            onClick={loadDiagnostics}
            className="ml-auto text-sm text-blue-600 hover:text-blue-800"
          >
            Retry
          </button>
        </div>
      </Card>
    );
  }

  if (!diagnostics) {
    return null;
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Reconciliation Diagnostics</h3>
        <button
          onClick={loadDiagnostics}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Data Availability */}
      <div className="mb-4">
        <button
          onClick={() => toggleSection('data_availability')}
          className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Info className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-gray-900">Data Availability</span>
          </div>
          <span className="text-sm text-gray-500">
            {expandedSections.has('data_availability') ? '▼' : '▶'}
          </span>
        </button>
        {expandedSections.has('data_availability') && (
          <div className="mt-2 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {Object.entries(diagnostics.data_availability).map(([docType, data]) => (
                <div
                  key={docType}
                  className={`p-3 rounded border ${
                    data.has_data
                      ? 'bg-green-50 border-green-200'
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {data.has_data ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-600" />
                    )}
                    <span className="font-medium text-sm capitalize">
                      {docType.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600">
                    {data.has_data ? `${data.record_count} records` : 'No data'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {diagnostics.recommendations && diagnostics.recommendations.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('recommendations')}
            className="w-full flex items-center justify-between p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Info className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-gray-900">Recommendations</span>
              <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded">
                {diagnostics.recommendations.length}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {expandedSections.has('recommendations') ? '▼' : '▶'}
            </span>
          </button>
          {expandedSections.has('recommendations') && (
            <div className="mt-2 p-4 bg-blue-50 rounded-lg">
              <ul className="space-y-2">
                {diagnostics.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-blue-900 flex items-start gap-2">
                    <span className="text-blue-600 mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Missing Accounts */}
      {Object.keys(diagnostics.missing_accounts).some(
        key => diagnostics.missing_accounts[key].length > 0
      ) && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('missing_accounts')}
            className="w-full flex items-center justify-between p-3 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              <span className="font-medium text-gray-900">Missing Accounts</span>
              <span className="text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded">
                {Object.values(diagnostics.missing_accounts).reduce((sum, arr) => sum + arr.length, 0)}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {expandedSections.has('missing_accounts') ? '▼' : '▶'}
            </span>
          </button>
          {expandedSections.has('missing_accounts') && (
            <div className="mt-2 p-4 bg-yellow-50 rounded-lg">
              {Object.entries(diagnostics.missing_accounts).map(([docType, missing]) => {
                if (missing.length === 0) return null;
                return (
                  <div key={docType} className="mb-3 last:mb-0">
                    <div className="font-medium text-sm text-gray-900 mb-2 capitalize">
                      {docType.replace('_', ' ')}
                    </div>
                    <ul className="space-y-1">
                      {missing.map((account, idx) => (
                        <li key={idx} className="text-xs text-yellow-900 flex items-start gap-2">
                          <span className="text-yellow-600 mt-1">-</span>
                          <span>{account}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Suggested Fixes */}
      {diagnostics.suggested_fixes && diagnostics.suggested_fixes.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('suggested_fixes')}
            className="w-full flex items-center justify-between p-3 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="font-medium text-gray-900">Suggested Fixes</span>
              <span className="text-xs bg-green-200 text-green-800 px-2 py-0.5 rounded">
                {diagnostics.suggested_fixes.length}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {expandedSections.has('suggested_fixes') ? '▼' : '▶'}
            </span>
          </button>
          {expandedSections.has('suggested_fixes') && (
            <div className="mt-2 p-4 bg-green-50 rounded-lg space-y-3">
              {diagnostics.suggested_fixes.map((fix, idx) => (
                <div key={idx} className="p-3 bg-white rounded border border-green-200">
                  <div className="font-medium text-sm text-gray-900 mb-1">{fix.issue}</div>
                  <div className="text-xs text-gray-700 mb-2">{fix.suggestion}</div>
                  {fix.similar_accounts && fix.similar_accounts.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-green-200">
                      <div className="text-xs font-medium text-gray-700 mb-1">Similar accounts found:</div>
                      <ul className="space-y-1">
                        {fix.similar_accounts.map((similar, sIdx) => (
                          <li key={sIdx} className="text-xs text-gray-600 flex items-center gap-2">
                            <span className="text-green-600">→</span>
                            <span>
                              {similar.account_code}: {similar.account_name} 
                              <span className="text-gray-500 ml-1">
                                ({similar.confidence.toFixed(0)}% confidence)
                              </span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Learned Patterns */}
      {diagnostics.learned_patterns && diagnostics.learned_patterns.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => toggleSection('learned_patterns')}
            className="w-full flex items-center justify-between p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Info className="w-5 h-5 text-purple-600" />
              <span className="font-medium text-gray-900">Learned Patterns</span>
              <span className="text-xs bg-purple-200 text-purple-800 px-2 py-0.5 rounded">
                {diagnostics.learned_patterns.length}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {expandedSections.has('learned_patterns') ? '▼' : '▶'}
            </span>
          </button>
          {expandedSections.has('learned_patterns') && (
            <div className="mt-2 p-4 bg-purple-50 rounded-lg space-y-2">
              {diagnostics.learned_patterns.map((pattern, idx) => (
                <div key={idx} className="p-3 bg-white rounded border border-purple-200">
                  <div className="font-medium text-sm text-gray-900 mb-1">{pattern.pattern_name}</div>
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>
                      {pattern.source_document_type} → {pattern.target_document_type}
                    </div>
                    {pattern.source_account_code && (
                      <div>
                        Source: {pattern.source_account_code}
                        {pattern.target_account_code && ` → Target: ${pattern.target_account_code}`}
                      </div>
                    )}
                    <div className="flex items-center gap-4 mt-2">
                      <span>
                        Success Rate: <strong>{pattern.success_rate.toFixed(1)}%</strong>
                      </span>
                      <span>
                        Avg Confidence: <strong>{pattern.average_confidence.toFixed(1)}%</strong>
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

