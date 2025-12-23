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
  Download
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
  const [activeTab, setActiveTab] = useState<'overview' | 'matches' | 'discrepancies'>('overview');
  
  // Filters
  const [matchTypeFilter, setMatchTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

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
      
      const result = await forensicReconciliationService.runReconciliation(sessionId, {
        use_exact: true,
        use_fuzzy: true,
        use_calculated: true,
        use_inferred: true,
        use_rules: true
      });
      
      // Reload session, matches, and discrepancies
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
    } catch (err: any) {
      console.error('Failed to run reconciliation:', err);
      setError(err.response?.data?.detail || 'Failed to run reconciliation');
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
            </div>
          </div>
        </Card>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-semibold mb-1">Issue Detected</p>
                <p className="text-sm">{error}</p>
                <div className="mt-3 p-3 bg-red-100 rounded border border-red-200">
                  <p className="text-sm font-semibold mb-1">💡 Troubleshooting Steps:</p>
                  <ul className="text-sm list-disc list-inside space-y-1">
                    <li>Verify documents have been uploaded for this property and period</li>
                    <li>Check that documents have been processed/extracted (go to Data Control Center)</li>
                    <li>Ensure Balance Sheet and Income Statement data exists for cross-document matching</li>
                    <li>Try selecting a different period that has financial data</li>
                  </ul>
                </div>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-2 text-red-600 hover:text-red-800 text-xl font-bold flex-shrink-0"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Overview */}
        {dashboardData && (
          <ReconciliationDashboard
            dashboardData={dashboardData}
            healthScore={healthScore}
            onRunReconciliation={session ? () => handleRunReconciliation(session.id) : undefined}
            onCompleteSession={session ? handleCompleteSession : undefined}
          />
        )}

        {/* Health Score Gauge */}
        {healthScore !== null && (
          <div className="mb-6">
            <ReconciliationHealthGauge healthScore={healthScore} />
          </div>
        )}

        {/* Tabs */}
        {session && (
          <div className="mb-6">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                {[
                  { id: 'overview', label: 'Overview', icon: FileText },
                  { id: 'matches', label: 'Matches', icon: CheckCircle },
                  { id: 'discrepancies', label: 'Discrepancies', icon: AlertTriangle },
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
            {activeTab === 'matches' && (
              <>
                {matches.length === 0 && !loading && session && (
                  <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                    <div className="flex items-center gap-2 text-yellow-800">
                      <AlertTriangle className="w-5 h-5" />
                      <div>
                        <p className="font-semibold">No matches found</p>
                        <p className="text-sm mt-1">
                          {matchTypeFilter !== 'all' || statusFilter !== 'all' 
                            ? 'Try adjusting your filters or check if a reconciliation has been run for this session.'
                            : 'No matches were found. This could mean:'}
                        </p>
                        {matchTypeFilter === 'all' && statusFilter === 'all' && (
                          <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                            <li>No financial data exists for this property/period</li>
                            <li>Documents haven't been extracted yet</li>
                            <li>Account codes don't match expected patterns</li>
                            <li>Reconciliation hasn't been run yet - click "Start Reconciliation"</li>
                          </ul>
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

