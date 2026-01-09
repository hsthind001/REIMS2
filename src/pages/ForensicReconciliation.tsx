/**
 * Forensic Reconciliation Page
 * 
 * Main page for forensic financial document reconciliation across
 * Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.
 */

import { useState, useEffect } from 'react';
import { 
  RefreshCw, 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  TrendingUp,
  FileText,
  Filter,
  Download,
  ListChecks
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicReconciliationService, type ForensicReconciliationSession, type ForensicMatch, type ForensicDiscrepancy } from '../lib/forensic_reconciliation';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import ReconciliationDashboard from '../components/forensic/ReconciliationDashboard';
import MatchTable from '../components/forensic/MatchTable';
import DiscrepancyPanel from '../components/forensic/DiscrepancyPanel';
import MatchDetailModal from '../components/forensic/MatchDetailModal';
import ReconciliationHealthGauge from '../components/forensic/ReconciliationHealthGauge';
import ReconciliationWorkQueue from '../components/forensic/ReconciliationWorkQueue';
import ReconciliationFilters from '../components/forensic/ReconciliationFilters';
import EvidencePanel from '../components/forensic/EvidencePanel';
import ReconciliationDiagnostics from '../components/forensic/ReconciliationDiagnostics';
import ReconciliationRulesPanel from '../components/forensic/ReconciliationRulesPanel';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ForensicReconciliation() {
  // Property and period selection
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [periods, setPeriods] = useState<any[]>([]);
  
  // Session and data
  const [session, setSession] = useState<ForensicReconciliationSession | null>(null);
  const [matches, setMatches] = useState<ForensicMatch[]>([]);
  const [discrepancies, setDiscrepancies] = useState<ForensicDiscrepancy[]>([]);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<ForensicMatch | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'matches' | 'discrepancies' | 'cockpit' | 'rules'>('overview');
  
  // Cockpit filters
  const [cockpitSeverityFilter, setCockpitSeverityFilter] = useState<string>('all');
  const [cockpitTierFilter, setCockpitTierFilter] = useState<string>('all');
  const [cockpitNeedsMe, setCockpitNeedsMe] = useState<boolean>(false);
  const [cockpitCommitteeId, setCockpitCommitteeId] = useState<number | null>(null);
  const [cockpitSLADue, setCockpitSLADue] = useState<boolean>(false);
  
  // Filters
  const [matchTypeFilter, setMatchTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  
  // Data availability state
  const [dataAvailability, setDataAvailability] = useState<any>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedPropertyId) {
      setSelectedPeriodId(null); // Reset period when property changes
      setPeriods([]); // Clear periods
      loadPeriods(selectedPropertyId);
    } else {
      setSelectedPeriodId(null);
      setPeriods([]);
    }
  }, [selectedPropertyId]);

  useEffect(() => {
    if (selectedPropertyId && selectedPeriodId) {
      loadDashboard();
    }
  }, [selectedPropertyId, selectedPeriodId]);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0) {
        setSelectedPropertyId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load properties:', err);
      setError('Failed to load properties');
    }
  };

  const loadPeriods = async (propertyId: number) => {
    try {
      const data = await financialPeriodsService.listPeriods({ property_id: propertyId });
      setPeriods(data);
      if (data.length > 0) {
        // Sort by year and month descending, then select most recent
        const sorted = [...data].sort((a, b) => {
          if (a.period_year !== b.period_year) {
            return b.period_year - a.period_year;
          }
          return b.period_month - a.period_month;
        });
        setSelectedPeriodId(sorted[0].id);
      } else {
        setSelectedPeriodId(null);
        setError('No financial periods found for this property. Please create a period first.');
      }
    } catch (err: any) {
      console.error('Failed to load periods:', err);
      setError(err.response?.data?.detail || 'Failed to load financial periods');
      setPeriods([]);
      setSelectedPeriodId(null);
    }
  };

  const loadDashboard = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // First check data availability
      const availability = await forensicReconciliationService.checkDataAvailability(selectedPropertyId, selectedPeriodId);
      setDataAvailability(availability);
      
      if (!availability.can_reconcile) {
        const recommendations = availability.recommendations || [];
        setError(`No financial data available for reconciliation. ${recommendations.join(' ')}`);
        setDashboardData(null);
        setSession(null);
        setMatches([]);
        setDiscrepancies([]);
        setHealthScore(null);
        return;
      }
      
      const data = await forensicReconciliationService.getDashboard(selectedPropertyId, selectedPeriodId);
      setDashboardData(data);
      
      if (data.session_id) {
        // Load session details
        const sessionData = await forensicReconciliationService.getSession(data.session_id);
        setSession(sessionData);
        
        // Load matches and discrepancies
        await loadMatches(data.session_id);
        await loadDiscrepancies(data.session_id);
        
        // Load health score
        const healthData = await forensicReconciliationService.getHealthScore(selectedPropertyId, selectedPeriodId);
        setHealthScore(healthData.health_score);
      } else {
        // No session exists yet, but data is available
        setSession(null);
        setMatches([]);
        setDiscrepancies([]);
        setHealthScore(null);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const loadMatches = async (sessionId: number) => {
    try {
      const filters: any = {};
      if (matchTypeFilter !== 'all') filters.match_type = matchTypeFilter;
      if (statusFilter !== 'all') filters.status = statusFilter;
      
      const data = await forensicReconciliationService.getMatches(sessionId, filters);
      console.log(`Loaded ${data.matches?.length || 0} matches for session ${sessionId}`, data);
      setMatches(data.matches || []);
      
      if (data.matches && data.matches.length === 0 && data.total > 0) {
        console.warn('Filters may be hiding matches. Total matches:', data.total);
      }
    } catch (err: any) {
      console.error('Failed to load matches:', err);
      setError(err.response?.data?.detail || 'Failed to load matches');
      setMatches([]);
    }
  };

  const loadDiscrepancies = async (sessionId: number) => {
    try {
      const filters: any = {};
      if (severityFilter !== 'all') filters.severity = severityFilter;
      
      const data = await forensicReconciliationService.getDiscrepancies(sessionId, filters);
      setDiscrepancies(data.discrepancies);
    } catch (err) {
      console.error('Failed to load discrepancies:', err);
    }
  };

  const handleStartSession = async () => {
    if (!selectedPropertyId || !selectedPeriodId) {
      setError('Please select a property and period');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const newSession = await forensicReconciliationService.createSession({
        property_id: selectedPropertyId,
        period_id: selectedPeriodId,
        session_type: 'full_reconciliation'
      });
      
      setSession(newSession);
      
      // Run reconciliation
      await handleRunReconciliation(newSession.id);
    } catch (err: any) {
      console.error('Failed to start session:', err);
      setError(err.response?.data?.detail || 'Failed to start reconciliation session');
    } finally {
      setLoading(false);
    }
  };

  const handleRunReconciliation = async (sessionId: number) => {
    try {
      setLoading(true);
      setError(null); // Clear previous errors
      
      const result = await forensicReconciliationService.runReconciliation(sessionId, {
        use_exact: true,
        use_fuzzy: true,
        use_calculated: true,
        use_inferred: true,
        use_rules: true
      });
      
      // Check if we have matches even if there were warnings
      const matchCount = result?.summary?.total_matches || 0;
      const hasMatches = matchCount > 0;
      
      // If we have matches, clear error and show success
      if (hasMatches) {
        setError(null);
        // Show warning if there were issues but matches were stored
        if (result.warning || result.diagnostic?.matches_failed) {
          console.warn('Reconciliation completed with warnings:', result.warning || result.diagnostic);
        }
      } else {
        // No matches found - show diagnostic information
        const diagnostic = result?.diagnostic;
        if (diagnostic) {
          const reasons = diagnostic.possible_reasons || [];
          const recommendations = diagnostic.recommendations || [];
          const message = diagnostic.message || 'No matches found';
          
          setError(`${message}. ${reasons.join(' ')} ${recommendations.join(' ')}`);
        } else {
          setError('No matches found. Please check that documents have been uploaded and extracted.');
        }
      }
      
      // Reload session, matches, and discrepancies (even if there were errors)
      try {
        const sessionData = await forensicReconciliationService.getSession(sessionId);
        setSession(sessionData);
        
        await loadMatches(sessionId);
        
        // Validate matches to get discrepancies
        await forensicReconciliationService.validateSession(sessionId);
        await loadDiscrepancies(sessionId);
        
        // Reload health score
        if (selectedPropertyId && selectedPeriodId) {
          const healthData = await forensicReconciliationService.getHealthScore(selectedPropertyId, selectedPeriodId);
          setHealthScore(healthData.health_score);
        }
      } catch (reloadErr: any) {
        console.error('Failed to reload session data:', reloadErr);
        // Don't set error here - we want to show matches if they exist
      }
      
    } catch (err: any) {
      console.error('Failed to run reconciliation:', err);
      
      // Check if we have partial results (matches stored before error)
      const errorDetail = err.response?.data?.detail || err.message || 'Failed to run reconciliation';
      
      // Try to load matches anyway - they might have been stored before the error
      try {
        await loadMatches(sessionId);
        const sessionData = await forensicReconciliationService.getSession(sessionId);
        const totalMatches = sessionData?.summary?.total_matches ?? 0;
        if (totalMatches > 0) {
          // We have matches! Show them with a warning
          setSession(sessionData);
          setError(`Reconciliation encountered an error, but ${totalMatches} matches were found. ${errorDetail}`);
        } else {
          // No matches, show full error
          setError(errorDetail);
        }
      } catch (loadErr) {
        // Can't load matches, show error
        setError(errorDetail);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApproveMatch = async (matchId: number) => {
    try {
      await forensicReconciliationService.approveMatch(matchId);
      if (session) {
        await loadMatches(session.id);
      }
    } catch (err: any) {
      console.error('Failed to approve match:', err);
      setError(err.response?.data?.detail || 'Failed to approve match');
    }
  };

  const handleRejectMatch = async (matchId: number, reason: string) => {
    try {
      await forensicReconciliationService.rejectMatch(matchId, { reason });
      if (session) {
        await loadMatches(session.id);
      }
    } catch (err: any) {
      console.error('Failed to reject match:', err);
      setError(err.response?.data?.detail || 'Failed to reject match');
    }
  };

  const handleResolveDiscrepancy = async (discrepancyId: number, resolutionNotes: string, newValue?: number) => {
    try {
      await forensicReconciliationService.resolveDiscrepancy(discrepancyId, {
        resolution_notes: resolutionNotes,
        new_value: newValue
      });
      if (session) {
        await loadDiscrepancies(session.id);
      }
    } catch (err: any) {
      console.error('Failed to resolve discrepancy:', err);
      setError(err.response?.data?.detail || 'Failed to resolve discrepancy');
    }
  };

  const handleCompleteSession = async () => {
    if (!session) return;
    
    try {
      setLoading(true);
      await forensicReconciliationService.completeSession(session.id);
      await loadDashboard();
    } catch (err: any) {
      console.error('Failed to complete session:', err);
      setError(err.response?.data?.detail || 'Failed to complete session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Forensic Reconciliation</h1>
          <p className="text-gray-600">
            Automated matching and reconciliation across Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement
          </p>
        </div>

        {/* Property and Period Selection */}
        <Card className="mb-6 p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Property</label>
              <select
                value={selectedPropertyId || ''}
                onChange={(e) => setSelectedPropertyId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Property</option>
                {properties.map(prop => (
                  <option key={prop.id} value={prop.id}>
                    {prop.property_code} - {prop.property_name}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Period</label>
              <select
                value={selectedPeriodId || ''}
                onChange={(e) => {
                  const periodId = e.target.value ? Number(e.target.value) : null;
                  setSelectedPeriodId(periodId);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                disabled={!selectedPropertyId || loading}
              >
                <option value="">{periods.length === 0 && selectedPropertyId ? 'Loading periods...' : 'Select Period'}</option>
                {periods.map(period => (
                  <option key={period.id} value={period.id}>
                    {period.period_year}-{String(period.period_month).padStart(2, '0')}
                  </option>
                ))}
              </select>
              {selectedPropertyId && periods.length === 0 && !loading && (
                <p className="mt-1 text-sm text-gray-500">No periods available. Create a financial period first.</p>
              )}
            </div>
            
            <div className="flex items-end">
              <Button
                onClick={handleStartSession}
                disabled={!selectedPropertyId || !selectedPeriodId || loading || periods.length === 0}
                isLoading={loading}
                icon={<Play className="w-4 h-4" />}
                title={!selectedPropertyId ? 'Select a property first' : !selectedPeriodId ? 'Select a period first' : periods.length === 0 ? 'No periods available' : 'Start reconciliation'}
              >
                Start Reconciliation
              </Button>
            </div>
            
            <div className="flex items-end gap-2">
              <Button
                onClick={loadDashboard}
                disabled={!selectedPropertyId || !selectedPeriodId || loading}
                variant="info"
                icon={<RefreshCw className="w-4 h-4" />}
              >
                Refresh
              </Button>
              {error && (
                <Button
                  onClick={() => window.location.hash = ''}
                  variant="secondary"
                  className="bg-green-600 text-white hover:bg-green-700"
                  title="Go to Data Control Center to upload documents"
                >
                  📤 Upload Documents
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Error Display with Enhanced Guidance - Only show if no matches */}
        {error && (!session || !matches || matches.length === 0) && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 mt-0.5 flex-shrink-0 text-yellow-600" />
              <div className="flex-1">
                <p className="font-semibold mb-2 text-yellow-900 text-lg">⚠️ Issue Detected</p>
                <p className="text-sm text-yellow-800 mb-4">{error}</p>
                
                {/* Data Availability Details */}
                {dataAvailability && (
                  <div className="mb-4 p-3 bg-white rounded border border-yellow-200">
                    <p className="text-sm font-semibold mb-2 text-gray-700">📊 Data Availability Status:</p>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                      {Object.entries(dataAvailability.document_uploads || {}).map(([docType, hasUpload]: [string, any]) => (
                        <div key={docType} className={`p-2 rounded ${hasUpload ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-500'}`}>
                          <div className="font-medium capitalize">{docType.replace('_', ' ')}</div>
                          <div className="text-xs mt-1">{hasUpload ? '✓ Uploaded' : '✗ Missing'}</div>
                        </div>
                      ))}
                    </div>
                    {dataAvailability.extracted_data && (
                      <div className="mt-3 pt-3 border-t border-yellow-200">
                        <p className="text-xs font-semibold mb-2 text-gray-700">📥 Extracted Data Records:</p>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                          {Object.entries(dataAvailability.extracted_data).map(([docType, data]: [string, any]) => (
                            <div key={docType} className={`p-2 rounded ${data.has_data ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-500'}`}>
                              <div className="font-medium capitalize">{docType.replace('_', ' ')}</div>
                              <div className="text-xs mt-1">{data.has_data ? `${data.count} records` : 'No data'}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Quick Start Guide */}
                <div className="mt-4 p-4 bg-blue-50 rounded border border-blue-200">
                  <p className="text-sm font-semibold mb-3 text-blue-900">🚀 Quick Start Guide:</p>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">1</div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900 mb-1">Upload Financial Documents</p>
                        <p className="text-xs text-blue-700 mb-2">Go to <strong>Data Control Center → Documents</strong> tab and upload at least:</p>
                        <ul className="text-xs text-blue-700 list-disc list-inside ml-2 space-y-1">
                          <li>Balance Sheet (required)</li>
                          <li>Income Statement (required)</li>
                        </ul>
                        <button
                          onClick={() => window.location.hash = ''}
                          className="mt-2 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                          📤 Go to Document Upload
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">2</div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900 mb-1">Wait for Document Extraction</p>
                        <p className="text-xs text-blue-700 mb-2">Documents are automatically processed. Check extraction status:</p>
                        <button
                          onClick={() => window.location.hash = ''}
                          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                          🔍 Check Extraction Status
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">3</div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900 mb-1">Start Reconciliation</p>
                        <p className="text-xs text-blue-700">Once extraction completes, return here and click <strong>"Start Reconciliation"</strong> button above.</p>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Troubleshooting Steps */}
                <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
                  <p className="text-sm font-semibold mb-2 text-gray-700">💡 Additional Troubleshooting:</p>
                  <ul className="text-xs text-gray-600 list-disc list-inside space-y-1">
                    <li>Verify documents have been uploaded for this property and period</li>
                    <li>Check that documents have been processed/extracted (go to Data Control Center → Tasks)</li>
                    <li>Ensure Balance Sheet and Income Statement data exists for cross-document matching</li>
                    <li>Try selecting a different period that has financial data</li>
                    <li>Check extraction task status in Data Control Center → Tasks tab</li>
                  </ul>
                </div>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-2 text-yellow-600 hover:text-yellow-800 text-xl font-bold flex-shrink-0"
                title="Dismiss"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Success/Warning Message - Show if matches found but there was a warning */}
        {session && matches && matches.length > 0 && error && (
          <div className="mb-6 p-4 bg-green-50 border border-green-300 rounded-lg">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-6 h-6 mt-0.5 flex-shrink-0 text-green-600" />
              <div className="flex-1">
                <p className="font-semibold mb-2 text-green-900 text-lg">✅ Matches Found</p>
                <p className="text-sm text-green-800 mb-2">
                  Found {matches.length} match{matches.length !== 1 ? 'es' : ''} for this reconciliation.
                </p>
                {error && (
                  <p className="text-xs text-green-700 italic">
                    Note: {error}
                  </p>
                )}
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-2 text-green-600 hover:text-green-800 text-xl font-bold flex-shrink-0"
                title="Dismiss"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Overview */}
        {dashboardData && (
          <>
            <ReconciliationDashboard
              dashboardData={dashboardData}
              healthScore={healthScore}
              onRunReconciliation={session ? () => handleRunReconciliation(session.id) : undefined}
              onCompleteSession={session ? handleCompleteSession : undefined}
            />
            {/* Show helpful message if no session exists but data is available */}
            {!session && dataAvailability && dataAvailability.can_reconcile && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">!</div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-blue-900 mb-1">✅ Data Available - Ready to Reconcile</p>
                    <p className="text-xs text-blue-700 mb-2">
                      Financial data has been extracted and is ready for reconciliation. Click <strong>"Start Reconciliation"</strong> above to begin.
                    </p>
                    <div className="text-xs text-blue-600">
                      <p className="font-medium mb-1">Available document types:</p>
                      <ul className="list-disc list-inside ml-2 space-y-0.5">
                        {Object.entries(dataAvailability.extracted_data || {}).map(([docType, data]: [string, any]) => 
                          data.has_data && (
                            <li key={docType} className="capitalize">
                              {docType.replace('_', ' ')} ({data.count} records)
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Health Score Gauge */}
        {healthScore !== null && (
          <div className="mb-6">
            <ReconciliationHealthGauge healthScore={healthScore} />
          </div>
        )}

        {/* Diagnostics Panel - Show when there's an error or when session exists */}
        {selectedPropertyId && selectedPeriodId && (error || session) && (
          <div className="mb-6">
            <ReconciliationDiagnostics
              propertyId={selectedPropertyId}
              periodId={selectedPeriodId}
              onRefresh={loadDashboard}
            />
          </div>
        )}

        {/* Tabs */}
        {session && (
          <div className="mb-6">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                {[
                  { id: 'overview', label: 'Overview', icon: FileText },
                  { id: 'cockpit', label: 'Cockpit', icon: TrendingUp },
                  { id: 'matches', label: 'Matches', icon: CheckCircle },
                  { id: 'discrepancies', label: 'Discrepancies', icon: AlertTriangle },
                  { id: 'rules', label: 'Rules', icon: ListChecks },
                ].map(tab => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                        ${activeTab === tab.id
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }
                      `}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {session && (
          <div>
            {activeTab === 'cockpit' && (
              <div className="grid grid-cols-12 gap-6">
                {/* Left Rail - Filters */}
                <div className="col-span-3">
                  <ReconciliationFilters
                    properties={properties}
                    periods={periods}
                    selectedPropertyId={selectedPropertyId}
                    selectedPeriodId={selectedPeriodId}
                    onPropertyChange={setSelectedPropertyId}
                    onPeriodChange={setSelectedPeriodId}
                    onSeverityFilter={setCockpitSeverityFilter}
                    onTierFilter={setCockpitTierFilter}
                    onNeedsMeFilter={setCockpitNeedsMe}
                    onCommitteeFilter={setCockpitCommitteeId}
                    onSLAFilter={setCockpitSLADue}
                    severityFilter={cockpitSeverityFilter}
                    tierFilter={cockpitTierFilter}
                    needsMe={cockpitNeedsMe}
                    committeeId={cockpitCommitteeId}
                    slaDue={cockpitSLADue}
                  />
                </div>

                {/* Center - Work Queue */}
                <div className="col-span-6">
                  <ReconciliationWorkQueue
                    matches={matches}
                    discrepancies={discrepancies}
                    onApprove={handleApproveMatch}
                    onReject={handleRejectMatch}
                    onViewDetails={setSelectedMatch}
                    filters={{
                      severity: cockpitSeverityFilter !== 'all' ? cockpitSeverityFilter : undefined,
                      tier: cockpitTierFilter !== 'all' ? cockpitTierFilter : undefined,
                      needsMe: cockpitNeedsMe,
                      assignedTo: cockpitCommitteeId || undefined
                    }}
                  />
                </div>

                {/* Right Panel - Evidence */}
                <div className="col-span-3">
                  <EvidencePanel
                    match={selectedMatch}
                    onApprove={handleApproveMatch}
                    onReject={handleRejectMatch}
                  />
                </div>
              </div>
            )}
            
            {activeTab === 'matches' && (
              <>
                {/* Match Statistics Banner */}
                {matches.length > 0 && session && (
                  <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <div>
                          <p className="font-semibold text-green-900">
                            {matches.length} Match{matches.length !== 1 ? 'es' : ''} Found
                          </p>
                          {session.summary && (
                            <div className="text-xs text-green-700 mt-1 flex items-center gap-4">
                              <span>Exact: {session.summary.exact_matches || 0}</span>
                              <span>Fuzzy: {session.summary.fuzzy_matches || 0}</span>
                              <span>Calculated: {session.summary.calculated_matches || 0}</span>
                              <span>Inferred: {session.summary.inferred_matches || 0}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      {session.summary && (
                        <div className="text-right">
                          <div className="text-sm font-medium text-green-900">
                            {session.summary.approved || 0} Approved
                          </div>
                          <div className="text-xs text-green-700">
                            {session.summary.pending_review || 0} Pending
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {matches.length === 0 && !loading && session && (
                  <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                    <div className="flex items-start gap-3 text-yellow-800">
                      <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="font-semibold mb-1">No matches found</p>
                        <p className="text-sm mb-3">
                          {matchTypeFilter !== 'all' || statusFilter !== 'all' 
                            ? 'Try adjusting your filters or check if a reconciliation has been run for this session.'
                            : 'No matches were found for this session. This could mean:'}
                        </p>
                        {matchTypeFilter === 'all' && statusFilter === 'all' && (
                          <div className="text-xs space-y-2">
                            <ul className="list-disc list-inside space-y-1 ml-2">
                              <li>Reconciliation hasn't been run yet - click "Run Reconciliation" button</li>
                              <li>Only one document type uploaded - need multiple documents for cross-document matching</li>
                              <li>Account codes don't match between documents</li>
                              <li>Amounts are outside tolerance thresholds</li>
                            </ul>
                            {(!session.summary || session.summary.total_matches === 0) && (
                              <div className="mt-3 p-2 bg-yellow-100 rounded border border-yellow-300">
                                <p className="font-medium mb-1">💡 Next Steps:</p>
                                <p className="text-xs">1. Ensure you have uploaded at least Balance Sheet and Income Statement</p>
                                <p className="text-xs">2. Verify documents have been extracted (check Data Control Center → Tasks)</p>
                                <p className="text-xs">3. Click "Run Reconciliation" button in the dashboard above</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                <MatchTable
                  matches={matches}
                  loading={loading}
                  onApprove={handleApproveMatch}
                  onReject={handleRejectMatch}
                  onViewDetails={setSelectedMatch}
                  matchTypeFilter={matchTypeFilter}
                  statusFilter={statusFilter}
                  onFilterChange={(type, status) => {
                    setMatchTypeFilter(type);
                    setStatusFilter(status);
                    if (session) loadMatches(session.id);
                  }}
                />
              </>
            )}
            
            {activeTab === 'discrepancies' && (
              <DiscrepancyPanel
                discrepancies={discrepancies}
                loading={loading}
                onResolve={handleResolveDiscrepancy}
                severityFilter={severityFilter}
                onFilterChange={(severity) => {
                  setSeverityFilter(severity);
                  if (session) loadDiscrepancies(session.id);
                }}
              />
            )}

            {activeTab === 'rules' && selectedPropertyId && selectedPeriodId && (
              <ReconciliationRulesPanel
                propertyId={selectedPropertyId}
                periodId={selectedPeriodId}
              />
            )}
          </div>
        )}

        {/* Match Detail Modal */}
        {selectedMatch && (
          <MatchDetailModal
            match={selectedMatch}
            onClose={() => setSelectedMatch(null)}
            onApprove={() => {
              if (selectedMatch) {
                handleApproveMatch(selectedMatch.id);
                setSelectedMatch(null);
              }
            }}
            onReject={(reason) => {
              if (selectedMatch) {
                handleRejectMatch(selectedMatch.id, reason);
                setSelectedMatch(null);
              }
            }}
          />
        )}
      </div>
    </div>
  );
}
