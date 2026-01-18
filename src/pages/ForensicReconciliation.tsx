/**
 * Forensic Reconciliation Page
 * 
 * Main page for forensic financial document reconciliation across
 * Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement.
 */

import { useState } from 'react';
import { 
  RefreshCw, 
  Play, 
  CheckCircle, 
  AlertTriangle,
  TrendingUp,
  FileText,
  ListChecks
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Card, Button } from '../components/design-system';
import { type ForensicMatch, type ForensicDiscrepancy } from '../lib/forensic_reconciliation';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import ReconciliationDashboard from '../components/forensic/ReconciliationDashboard';
import MatchTable from '../components/forensic/MatchTable';
import MatchDetailModal from '../components/forensic/MatchDetailModal';
import ReconciliationHealthGauge from '../components/forensic/ReconciliationHealthGauge';
import ReconciliationWorkQueue from '../components/forensic/ReconciliationWorkQueue';
import ReconciliationFilters from '../components/forensic/ReconciliationFilters';
import EvidencePanel from '../components/forensic/EvidencePanel';
import ReconciliationDiagnostics from '../components/forensic/ReconciliationDiagnostics';
import ReconciliationRulesPanel from '../components/forensic/ReconciliationRulesPanel';
import {
  useForensicDashboard,
  useForensicSession,
  useForensicMatches,
  useForensicDiscrepancies,
  useForensicHealthScore,
  useForensicMutations
} from '../hooks/useForensicReconciliation';

export default function ForensicReconciliation() {
  // Selection state
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  
  // UI state
  const [selectedMatch, setSelectedMatch] = useState<ForensicMatch | null>(null);
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<ForensicDiscrepancy | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'matches' | 'discrepancies' | 'cockpit' | 'rules'>('overview');
  
  // Filter state
  const [cockpitSeverityFilter, setCockpitSeverityFilter] = useState<string>('all');
  const [cockpitTierFilter, setCockpitTierFilter] = useState<string>('all');
  const [cockpitNeedsMe, setCockpitNeedsMe] = useState<boolean>(false);
  const [cockpitCommitteeId, setCockpitCommitteeId] = useState<number | null>(null);
  const [cockpitSLADue, setCockpitSLADue] = useState<boolean>(false);
  const [matchTypeFilter, setMatchTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  // Queries
  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['properties'],
    queryFn: () => propertyService.getAllProperties(),
  });

  // Effect to select first property
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const [initialPropertySet, setInitialPropertySet] = useState(false);
  if (properties.length > 0 && !selectedPropertyId && !initialPropertySet) {
      setSelectedPropertyId(properties[0].id);
      setInitialPropertySet(true);
  }

  const { data: periods = [], isLoading: periodsLoading } = useQuery<any[]>({
    queryKey: ['periods', selectedPropertyId],
    queryFn: () => financialPeriodsService.listPeriods({ property_id: selectedPropertyId! }),
    enabled: !!selectedPropertyId,
  });

  // Effect to select first period
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const [lastSelectedPropertyForPeriod, setLastSelectedPropertyForPeriod] = useState<number | null>(null);
  if (periods.length > 0 && selectedPropertyId && lastSelectedPropertyForPeriod !== selectedPropertyId) {
       const sorted = [...periods].sort((a, b) => {
         if (a.period_year !== b.period_year) return b.period_year - a.period_year;
         return b.period_month - a.period_month;
       });
       if (sorted.length > 0) {
           setSelectedPeriodId(sorted[0].id);
       }
       setLastSelectedPropertyForPeriod(selectedPropertyId);
  } else if (periods.length === 0 && selectedPropertyId && lastSelectedPropertyForPeriod !== selectedPropertyId && !periodsLoading) {
      // If loaded and empty, clear selection
      setSelectedPeriodId(null);
      setLastSelectedPropertyForPeriod(selectedPropertyId);
  }

  // const { data: dataAvailability } = useForensicDataAvailability(selectedPropertyId, selectedPeriodId);
  
  const { 
    data: dashboardData, 
    isLoading: dashboardLoading, 
    error: dashboardError,
    refetch: refetchDashboard
  } = useForensicDashboard(selectedPropertyId, selectedPeriodId);

  const sessionId = dashboardData?.session_id || null;

  const { data: session } = useForensicSession(sessionId);
  
  const matchFilters = {
    match_type: matchTypeFilter !== 'all' ? matchTypeFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined
  };
  const { data: matchesData, isLoading: matchesLoading } = useForensicMatches(sessionId, matchFilters);
  const matches = matchesData?.matches || [];

  const discrepancyFilters = {
    severity: severityFilter !== 'all' ? severityFilter : undefined
  };
  const { data: discrepanciesData } = useForensicDiscrepancies(sessionId, discrepancyFilters);
  const discrepancies = discrepanciesData?.discrepancies || [];

  const { data: healthData } = useForensicHealthScore(selectedPropertyId, selectedPeriodId);
  const healthScore = healthData?.health_score;

  // Mutations
  const { 
    createSession, 
    runReconciliation, 
    approveMatch, 
    rejectMatch, 
    completeSession
  } = useForensicMutations();

  // Handlers
  const handleStartSession = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;
    try {
      const newSession = await createSession.mutateAsync({
         property_id: selectedPropertyId,
         period_id: selectedPeriodId,
         session_type: 'full_reconciliation'
      });
      if (newSession.id) {
          handleRunReconciliation(newSession.id);
      }
    } catch (err) {
      console.error("Error starting session", err);
    }
  };

  const handleRunReconciliation = async (sessId: number) => {
    try {
      await runReconciliation.mutateAsync({
        sessionId: sessId,
        options: {
          use_exact: true,
          use_fuzzy: true,
          use_calculated: true,
          use_inferred: true,
          use_rules: true
        }
      });
    } catch (err) {
      console.error("Error running reconciliation", err);
    }
  };

  const handleApproveMatch = (matchId: number) => {
    approveMatch.mutate({ matchId });
    if (selectedMatch?.id === matchId) setSelectedMatch(null);
  };

  const handleRejectMatch = (matchId: number, reason: string) => {
    rejectMatch.mutate({ matchId, reason });
    if (selectedMatch?.id === matchId) setSelectedMatch(null);
  };

  const handleViewDetails = (item: ForensicMatch | ForensicDiscrepancy) => {
    if ('source_document_type' in item) {
      setSelectedMatch(item as ForensicMatch);
      setSelectedDiscrepancy(null);
    } else {
      setSelectedDiscrepancy(item as ForensicDiscrepancy);
      setSelectedMatch(null);
    }
  };

  const handleCompleteSession = () => {
      if (session) {
          completeSession.mutate(session.id);
      }
  };

  const loading = dashboardLoading || matchesLoading || createSession.isPending || runReconciliation.isPending;

  const error = dashboardError ? (dashboardError as any).message || 'Error loading dashboard' : null;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Forensic Reconciliation</h1>
          <p className="text-gray-600">
            Automated matching and reconciliation across Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement
          </p>
        </div>

        <Card className="mb-6 p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Property</label>
              <select
                value={selectedPropertyId || ''}
                onChange={(e) => setSelectedPropertyId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">Select Property</option>
                {properties.map(prop => (
                  <option key={prop.id} value={prop.id}>{prop.property_code} - {prop.property_name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Period</label>
              <select
                value={selectedPeriodId || ''}
                onChange={(e) => setSelectedPeriodId(e.target.value ? Number(e.target.value) : null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                disabled={!selectedPropertyId}
              >
                <option value="">{periodsLoading ? 'Loading...' : 'Select Period'}</option>
                {periods.map(period => (
                  <option key={period.id} value={period.id}>{period.period_year}-{String(period.period_month).padStart(2, '0')}</option>
                ))}
              </select>
            </div>
            
            <div className="flex items-end">
              <Button
                onClick={handleStartSession}
                disabled={!selectedPropertyId || !selectedPeriodId || loading}
                isLoading={createSession.isPending}
                icon={<Play className="w-4 h-4" />}
              >
                Start Reconciliation
              </Button>
            </div>
            
            <div className="flex items-end gap-2">
              <Button
                onClick={() => refetchDashboard()}
                disabled={loading}
                variant="info"
                icon={<RefreshCw className="w-4 h-4" />}
              >
                Refresh
              </Button>
            </div>
          </div>
        </Card>

        {error && (!matches || matches.length === 0) && (
             <div className="mb-6 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-6 h-6 text-yellow-600" />
                    <div>
                        <p className="font-semibold text-yellow-900">Issue Detected</p>
                        <p className="text-sm text-yellow-800">{error}</p>
                    </div>
                </div>
             </div>
        )}

        {dashboardData && (
          <ReconciliationDashboard
            dashboardData={dashboardData}
            healthScore={healthScore}
            onRunReconciliation={session ? () => handleRunReconciliation(session.id) : undefined}
            onCompleteSession={session ? handleCompleteSession : undefined}
            onRefresh={refetchDashboard}
          />
        )}

        {typeof healthScore === 'number' && (
          <div className="mb-6">
            <ReconciliationHealthGauge healthScore={healthScore} />
          </div>
        )}

        {selectedPropertyId && selectedPeriodId && (error || session) && (
          <div className="mb-6">
            <ReconciliationDiagnostics
              propertyId={selectedPropertyId}
              periodId={selectedPeriodId}
              onRefresh={refetchDashboard}
            />
          </div>
        )}

        {session && (
          <>
            <div className="mb-6 sticky top-0 z-30 bg-gray-50/95 border-b border-gray-200">
                <nav className="flex gap-4">
                    {[{id:'overview', label:'Overview', icon:FileText}, {id:'cockpit', label:'Cockpit', icon:TrendingUp}, {id:'matches', label:'Matches', icon:CheckCircle}, {id:'rules', label:'Rules', icon:ListChecks}].map(tab => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={`flex items-center gap-2 py-3 px-3 border-b-2 font-semibold text-sm ${activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}
                            >
                                <Icon className="w-4 h-4" /> {tab.label}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {activeTab === 'cockpit' && (
                <div className="grid grid-cols-12 gap-6">
                    <div className="col-span-3">
                        <ReconciliationFilters
                             properties={properties as any[]}
                             periods={periods as any[]}
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
                    <div className="col-span-6">
                        <ReconciliationWorkQueue
                            matches={matches as any[]}
                            discrepancies={discrepancies as any[]}
                            onApprove={handleApproveMatch}
                            onReject={handleRejectMatch}
                            onViewDetails={handleViewDetails}
                            filters={{
                                severity: cockpitSeverityFilter !== 'all' ? cockpitSeverityFilter : undefined,
                                tier: cockpitTierFilter !== 'all' ? cockpitTierFilter : undefined,
                                needsMe: cockpitNeedsMe,
                                assignedTo: cockpitCommitteeId || undefined
                            }}
                        />
                    </div>
                    <div className="col-span-3">
                        <EvidencePanel
                            match={selectedMatch}
                            discrepancy={selectedDiscrepancy}
                            onApprove={handleApproveMatch}
                            onReject={handleRejectMatch}
                        />
                    </div>
                </div>
            )}

            {activeTab === 'matches' && (
                <MatchTable
                    matches={matches as any[]}
                    loading={matchesLoading}
                    onApprove={handleApproveMatch}
                    onReject={handleRejectMatch}
                    onViewDetails={setSelectedMatch}
                    matchTypeFilter={matchTypeFilter}
                    statusFilter={statusFilter}
                    onFilterChange={(type, status) => {
                        setMatchTypeFilter(type);
                        setStatusFilter(status);
                    }}
                />
            )}

            {activeTab === 'rules' && selectedPropertyId && selectedPeriodId && (
                <ReconciliationRulesPanel
                    propertyId={selectedPropertyId}
                    periodId={selectedPeriodId}
                />
            )}
          </>
        )}

        {selectedMatch && (
            <MatchDetailModal
                match={selectedMatch}
                onClose={() => setSelectedMatch(null)}
                onApprove={() => handleApproveMatch(selectedMatch.id)}
                onReject={(reason) => handleRejectMatch(selectedMatch.id, reason)}
            />
        )}
      </div>
    </div>
  );
}
