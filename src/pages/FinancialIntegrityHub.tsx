import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import HeaderControlPanel from '../components/financial_integrity/HeaderControlPanel';
import IntegrityScoreBanner from '../components/financial_integrity/IntegrityScoreBanner';
import ReconciliationMatrix from '../components/financial_integrity/ReconciliationMatrix';
import OverviewTab from '../components/financial_integrity/tabs/OverviewTab';
import ByDocumentTab from '../components/financial_integrity/tabs/ByDocumentTab';
import ByRuleTab from '../components/financial_integrity/tabs/ByRuleTab';
import ExceptionsTab from '../components/financial_integrity/tabs/ExceptionsTab';
import InsightsTab from '../components/financial_integrity/tabs/InsightsTab';
import RuleDetailModal from '../components/financial_integrity/modals/RuleDetailModal';
import DocumentPairPanel from '../components/financial_integrity/panels/DocumentPairPanel';
import { 
    useForensicDashboard, 
    useForensicMutations,
    useForensicMatches,
    useForensicDiscrepancies,
    useForensicHealthScore,
    useForensicCalculatedRules
} from '../hooks/useForensicReconciliation';

export default function FinancialIntegrityHub() {
    // State
    const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null);
    const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
    const [isValidating, setIsValidating] = useState(false);
    
    // UI State
    const [activeTab, setActiveTab] = useState('overview');
    const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
    const [selectedPair, setSelectedPair] = useState<{source: string, target: string, value: number} | null>(null);

    // Queries
    const { data: properties = [] } = useQuery<Property[]>({
        queryKey: ['properties'],
        queryFn: () => propertyService.getAllProperties(),
    });

    const { data: periods = [] } = useQuery<any[]>({
        queryKey: ['periods', selectedPropertyId],
        queryFn: () => financialPeriodsService.listPeriods({ property_id: selectedPropertyId! }),
        enabled: !!selectedPropertyId,
    });

    // Auto-select logic
    useEffect(() => {
        if (properties.length > 0 && !selectedPropertyId) {
            setSelectedPropertyId(properties[0].id);
        }
    }, [properties, selectedPropertyId]);

    useEffect(() => {
        if (periods.length > 0 && !selectedPeriodId) {
            // Sort by most recent
            const sorted = [...periods].sort((a, b) => {
                if (a.period_year !== b.period_year) return b.period_year - a.period_year;
                return b.period_month - a.period_month;
            });
            if (sorted.length > 0) setSelectedPeriodId(sorted[0].id);
        }
    }, [periods, selectedPeriodId]);

    // Forensic Queries
    const { data: dashboardData, isLoading: isLoadingDashboard } = useForensicDashboard(selectedPropertyId, selectedPeriodId);
    
    // We assume the session ID is available from dashboard or we fetch recent session logic
    // For now, let's assume dashboardData returns a session_id or we run a getSession call.
    // In current mock/API, dashboardData has session_id.
    const sessionId = dashboardData?.session_id || null;

    const { data: matchesData } = useForensicMatches(sessionId);
    const { data: discrepanciesData } = useForensicDiscrepancies(sessionId);
    const { data: healthScoreData } = useForensicHealthScore(selectedPropertyId, selectedPeriodId);
    const { data: calculatedRulesData } = useForensicCalculatedRules(selectedPropertyId, selectedPeriodId);

    const matches = matchesData?.matches || [];
    const discrepancies = discrepanciesData?.discrepancies || [];
    const healthScore = healthScoreData?.overall_score || dashboardData?.summary?.health_score || 0;

    const { validateSession } = useForensicMutations();

    // Derived Data for Document Tab
    const documentStats = useMemo(() => {
        const stats: Record<string, { id: string, name: string, type: string, passed: number, failed: number, rules: number, lastSync: string }> = {};
        
        matches.forEach(m => {
            const docs = [m.source_document_type, m.target_document_type];
            docs.forEach(d => {
                if (!stats[d]) {
                     stats[d] = { 
                         id: d, 
                         name: d.replace(/_/g, ' '), 
                         type: 'Financial', // Infer from name?
                         passed: 0, 
                         failed: 0, 
                         rules: 0, 
                         lastSync: 'Now' 
                     };
                }
                if (m.status === 'approved' || m.confidence_score === 1.0) {
                    stats[d].passed++;
                } else {
                    stats[d].failed++;
                }
                stats[d].rules++; // Rough proxy
            });
        });

        // Add any missing from documents list if we had a static list?
        // For now return array
        return Object.values(stats);
    }, [matches]);

    const handleValidate = async () => {
        if (!sessionId) return;
        setIsValidating(true);
        try {
            await validateSession.mutateAsync(sessionId);
            // potentially refetch checks here
        } catch (error) {
            console.error("Validation failed", error);
        } finally {
            setIsValidating(false);
        }
    };

    const handleCellClick = (source: string, target: string, value: number) => {
        setSelectedPair({ source, target, value });
    };

    return (
        <div className="min-h-screen bg-gray-50/50 pb-20">
            <HeaderControlPanel
                properties={properties}
                selectedPropertyId={selectedPropertyId}
                selectedPeriodId={selectedPeriodId}
                periods={periods}
                onPropertyChange={setSelectedPropertyId}
                onPeriodChange={setSelectedPeriodId}
                onValidate={handleValidate}
                isValidating={isValidating}
                onExport={(format) => console.log(`Exporting as ${format}`)}
            />

            <main className="max-w-[1920px] mx-auto px-6 py-8 space-y-8">

                {/* Integrity Banner */}
                <IntegrityScoreBanner
                    score={healthScore}
                    matchCount={matches.length}
                    discrepancyCount={discrepancies.length}
                    timingCount={discrepancies.filter(d => d.severity === 'low').length} // Approximation
                    activeRulesCount={calculatedRulesData?.rules?.length || 0}
                    lastValidated={dashboardData?.started_at}
                    onViewExceptions={() => setActiveTab('exceptions')}
                />

                {/* Main Content Grid */}
                <div className="grid grid-cols-12 gap-8">
                    {/* Left Col: Matrix */}
                    <div className="col-span-12 xl:col-span-5">
                         <ReconciliationMatrix
                            matches={matches}
                            onCellClick={handleCellClick}
                         />
                    </div>

                    {/* Right Col: Tab Content */}
                    <div className="col-span-12 xl:col-span-7 flex flex-col gap-6">

                         {/* Tab Navigation */}
                         <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-1.5 flex items-center gap-1 overflow-x-auto">
                            {[
                                { id: 'overview', label: 'Overview' },
                                { id: 'documents', label: 'By Document' },
                                { id: 'rules', label: 'By Rule' },
                                { id: 'exceptions', label: 'Exceptions' },
                                { id: 'insights', label: 'Insights' }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                                        activeTab === tab.id
                                        ? 'bg-blue-50 text-blue-700 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                                    }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                         </div>

                         {activeTab === 'overview' ? (
                             <OverviewTab 
                                healthScore={healthScore}
                                criticalItems={discrepancies.filter(d => d.severity === 'high')}
                                recentActivity={dashboardData?.recent_activity}
                             />
                         ) : activeTab === 'documents' ? (
                            <ByDocumentTab 
                                documents={documentStats}
                                rules={calculatedRulesData?.rules}
                            />
                        ) : activeTab === 'rules' ? (
                            <ByRuleTab 
                                rules={calculatedRulesData?.rules}
                                onRuleClick={(id) => setSelectedRuleId(id)}
                            />
                         ) : activeTab === 'exceptions' ? (
                             <ExceptionsTab 
                                discrepancies={discrepancies}
                             />
                         ) : (
                             <InsightsTab />
                         )}
                    </div>
                </div>

            </main>

            {/* Modals & Panels */}
            {selectedPair && (
                <DocumentPairPanel
                    isOpen={!!selectedPair}
                    onClose={() => setSelectedPair(null)}
                    pair={selectedPair}
                    matches={matches}
                />
            )}

            <RuleDetailModal
                isOpen={!!selectedRuleId}
                onClose={() => setSelectedRuleId(null)}
                ruleId={selectedRuleId || ''}
            />

        </div>
    );
}
