
import { useState, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import ReconciliationMatrix from '../components/financial_integrity/ReconciliationMatrix';
import OverviewTab from '../components/financial_integrity/tabs/OverviewTab';
import ByDocumentTab from '../components/financial_integrity/tabs/ByDocumentTab';
import ByRuleTab from '../components/financial_integrity/tabs/ByRuleTab';
import ExceptionsTab from '../components/financial_integrity/tabs/ExceptionsTab';
import InsightsTab from '../components/financial_integrity/tabs/InsightsTab';
import DocumentPairPanel from '../components/financial_integrity/panels/DocumentPairPanel';
import { 
    useForensicDashboard, 
    useForensicMutations,
    useForensicMatches,
    useForensicDiscrepancies,
    useForensicHealthScore,
    useForensicCalculatedRules
} from '../hooks/useForensicReconciliation';

import EditRuleModal from '../components/financial_integrity/modals/EditRuleModal';

// UI Components
import { Card, Button } from '../components/ui';
import HealthScoreGauge from '../components/forensic-audit/HealthScoreGauge';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import { 
    Download, 
    Play, 
    CheckCircle2, 
    Activity, 
    Clock
} from 'lucide-react';

export default function FinancialIntegrityHub() {
    const queryClient = useQueryClient();
    
    // State
    const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(() => {
        const saved = localStorage.getItem('forensic_selectedPropertyId');
        return saved ? Number(saved) : null;
    });
    const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(() => {
        const saved = localStorage.getItem('forensic_selectedPeriodId');
        return saved ? Number(saved) : null;
    });
    const [isValidating, setIsValidating] = useState(false);
    const [isRunningReconciliation, setIsRunningReconciliation] = useState(false);
    
    // UI State
    const [activeTab, setActiveTab] = useState('overview');
    const [selectedPair, setSelectedPair] = useState<{source: string, target: string, value: number} | null>(null);

    const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

    // Persist State
    useEffect(() => {
        if (selectedPropertyId) {
            localStorage.setItem('forensic_selectedPropertyId', String(selectedPropertyId));
        }
    }, [selectedPropertyId]);

    useEffect(() => {
        if (selectedPeriodId) {
            localStorage.setItem('forensic_selectedPeriodId', String(selectedPeriodId));
        }
    }, [selectedPeriodId]);

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
            // Only auto-select if we didn't restore from storage (checked by !selectedPropertyId state initialization)
            // But state init handles init. If it was null, we select first.
            setSelectedPropertyId(properties[0].id);
        }
    }, [properties, selectedPropertyId]);

    useEffect(() => {
        // If specific period was restored but isn't in the new list (e.g. property changed), we might need to reset.
        // However, the main logic is: if no period selected, pick most recent.
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
    const { data: dashboardData } = useForensicDashboard(selectedPropertyId, selectedPeriodId);
    
    const sessionId = dashboardData?.session_id || null;

    const { data: matchesData } = useForensicMatches(sessionId);
    const { data: discrepanciesData } = useForensicDiscrepancies(sessionId);
    const { data: healthScoreData } = useForensicHealthScore(selectedPropertyId, selectedPeriodId);
    const { data: calculatedRulesData } = useForensicCalculatedRules(selectedPropertyId, selectedPeriodId);

    const matches = useMemo(() => matchesData?.matches || [], [matchesData]);
    const discrepancies = discrepanciesData?.discrepancies || [];
    const healthScore = healthScoreData?.health_score || dashboardData?.summary?.health_score || 0;

    const { createSession, runReconciliation, validateSession, updateRule } = useForensicMutations();

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

        return Object.values(stats);
    }, [matches]);

    const handleRunReconciliation = async () => {
        if (!selectedPropertyId || !selectedPeriodId) return;
        
        setIsRunningReconciliation(true);
        try {
            let currentSessionId = sessionId;
            
            // If no session exists, create one
            if (!currentSessionId) {
                const newSession = await createSession.mutateAsync({
                    property_id: selectedPropertyId,
                    period_id: selectedPeriodId,
                    session_type: 'full_reconciliation'
                });
                
                currentSessionId = newSession.id;
            }
            
            // Run reconciliation to find matches
            if (currentSessionId) {
                await runReconciliation.mutateAsync({
                    sessionId: currentSessionId,
                    options: {
                        use_exact: true,
                        use_fuzzy: true,
                        use_calculated: true,
                        use_inferred: true,
                        use_rules: true
                    }
                });
                
                // Wait for matches to be stored, then refresh queries
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Manually refetch queries to ensure UI updates
                await queryClient.refetchQueries({ queryKey: ['forensic'] });
            }
        } catch (error) {
            console.error("Reconciliation failed", error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            alert(`Failed to run reconciliation: ${errorMessage}\n\nPlease check that documents have been uploaded and extracted for this property and period.`);
        } finally {
            setIsRunningReconciliation(false);
        }
    };

    const handleValidate = async () => {
        if (!selectedPropertyId || !selectedPeriodId || !sessionId) {
            alert("Please run reconciliation first to create matches, then validate.");
            return;
        }
        
        setIsValidating(true);
        try {
            // Validate the session (calculates health score from existing matches)
            await validateSession.mutateAsync(sessionId);
            
            // Refresh queries after validation
            await queryClient.refetchQueries({ queryKey: ['forensic'] });
        } catch (error) {
            console.error("Validation failed", error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            alert(`Failed to validate session: ${errorMessage}`);
        } finally {
            setIsValidating(false);
        }
    };

    const handleCellClick = (source: string, target: string, value: number) => {
        setSelectedPair({ source, target, value });
    };

    const getPropertyLabel = (property: Property): string => {
        return property.property_name || property.property_code || `Property ${property.id}`;
    };

    const formatPeriodLabel = (period: any): string => {
        if (period.period_year && period.period_month) {
            return `${period.period_year}-${String(period.period_month).padStart(2, '0')}`;
        }
        return `Period ${period.id}`;
    };

    const auditTabs = [
        { id: 'overview', label: 'Overview', icon: '📊' },
        { id: 'documents', label: 'By Document', icon: '📄' },
        { id: 'rules', label: 'By Rule', icon: '📋' },
        { id: 'exceptions', label: 'Exceptions', icon: '🚨' },
        { id: 'insights', label: 'Insights', icon: '💡' }
    ];

    const getStatusFromScore = (score: number) => {
        if (score >= 90) return { color: 'green', label: 'Pass' };
        if (score >= 70) return { color: 'yellow', label: 'Warning' };
        return { color: 'red', label: 'Fail' };
    };

    const status = getStatusFromScore(healthScore);

    const editingRule = useMemo(() => {
        if (!editingRuleId || !calculatedRulesData?.rules) return null;
        const rule = calculatedRulesData.rules.find(r => r.rule_id === editingRuleId);
        if (!rule) return null;
        
        // Map API response format to Modal format
        return {
            id: rule.rule_id,
            name: rule.rule_name,
            description: rule.description || '',
            formula: rule.formula,
            threshold: rule.tolerance_absolute || rule.tolerance_percent || 0,
            type: 'calculated'
        };
    }, [editingRuleId, calculatedRulesData]);


    const handleSaveRule = async (data: any) => {
        if (!editingRuleId) return;
        
        try {
            await updateRule.mutateAsync({
                ruleId: editingRuleId,
                data
            });
            // Toast success?
        } catch (error) {
            console.error("Failed to update rule", error);
            // Toast error?
        }
    };

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Financial Integrity Hub</h1>
                    <p className="text-gray-600 mt-1">Live Reconciliation & Validation</p>
                </div>

                <div className="flex items-center gap-4">
                    {/* Property Selector */}
                    <select
                        value={selectedPropertyId || ''}
                        onChange={(e) => setSelectedPropertyId(Number(e.target.value))}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        aria-label="Select Property"
                    >
                        <option value="">Select Property</option>
                        {properties.map((property) => (
                            <option key={property.id} value={property.id}>
                                {getPropertyLabel(property)}
                            </option>
                        ))}
                    </select>

                    {/* Period Selector */}
                    <select
                        value={selectedPeriodId || ''}
                        onChange={(e) => setSelectedPeriodId(Number(e.target.value))}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        disabled={!selectedPropertyId}
                        aria-label="Select Financial Period"
                    >
                        <option value="">Select Period</option>
                        {periods.map((period) => (
                            <option key={period.id} value={period.id}>
                                {formatPeriodLabel(period)}
                            </option>
                        ))}
                    </select>

                   {/* Actions */}
                    <Button
                        onClick={() => console.log('Exporting...')}
                        variant="secondary"
                        icon={<Download className="w-4 h-4" />}
                    >
                        Export
                    </Button>

                    <Button
                        onClick={handleValidate}
                        disabled={isValidating || !selectedPropertyId || !selectedPeriodId}
                        variant="warning"
                        loading={isValidating}
                        icon={<CheckCircle2 className="w-4 h-4" />}
                    >
                        {isValidating ? 'Validating...' : 'Validate'}
                    </Button>

                    <Button
                        onClick={handleRunReconciliation}
                        disabled={isRunningReconciliation || !selectedPropertyId || !selectedPeriodId}
                        variant="primary"
                        loading={isRunningReconciliation}
                        icon={<Play className="w-4 h-4" />}
                    >
                        {isRunningReconciliation ? 'Running...' : 'Run Reconciliation'}
                    </Button>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Integrity Score */}
                <Card className="p-6">
                    <div className="text-center">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Integrity Score</h3>
                        <HealthScoreGauge score={healthScore} size="lg" />
                         <div className="mt-4 text-sm text-gray-600">
                             {dashboardData?.started_at ? `Last validated ${new Date(dashboardData.started_at).toLocaleDateString()}` : 'Not validated yet'}
                        </div>
                    </div>
                </Card>

                 {/* Validation Status */}
                 <Card className="p-6">
                    <div className="text-center">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Status</h3>
                         <div className="flex justify-center mb-4">
                            <TrafficLightIndicator status={status.color.toUpperCase()} size="lg" showLabel />
                        </div>
                        <div className="mt-6 flex flex-col items-center gap-2">
                             <div className="flex items-center gap-2 text-sm text-gray-600">
                                <Activity className="w-4 h-4" />
                                <span>{calculatedRulesData?.rules?.length || 0} Rules Active</span>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Reconciliation Stats */}
                <Card className="p-6">
                     <div className="text-center">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Reconciliation Stats</h3>
                         <div className="grid grid-cols-2 gap-4 mt-2">
                             <div className="text-center p-3 bg-green-50 rounded-lg">
                                 <div className="text-2xl font-bold text-green-700">{matches.length}</div>
                                 <div className="text-xs text-green-600 font-medium uppercase mt-1">Verified Matches</div>
                             </div>
                             <div 
                                className="text-center p-3 bg-amber-50 rounded-lg cursor-pointer hover:bg-amber-100 transition-colors"
                                onClick={() => setActiveTab('exceptions')}
                            >
                                 <div className="text-2xl font-bold text-amber-700">{discrepancies.length}</div>
                                 <div className="text-xs text-amber-600 font-medium uppercase mt-1">Discrepancies</div>
                             </div>
                         </div>
                         <div className="mt-4 text-xs text-gray-500 flex items-center justify-center gap-1">
                             <Clock className="w-3 h-3" />
                             <span>{discrepancies.filter(d => d.severity === 'low').length} Pending Review</span>
                         </div>
                    </div>
                </Card>
            </div>

            {/* Navigation Tabs */}
            <div style={{
                display: 'flex',
                gap: '0.5rem',
                overflowX: 'auto',
                borderBottom: '2px solid #e5e7eb',
                paddingBottom: '0.5rem',
            }}>
                {auditTabs.map(tab => {
                    const isActive = activeTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                padding: '0.75rem 1rem',
                                border: 'none',
                                background: isActive ? '#3b82f6' : 'transparent',
                                color: isActive ? 'white' : '#6b7280',
                                fontWeight: 600,
                                fontSize: '0.875rem',
                                borderRadius: '8px 8px 0 0',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.2s',
                                borderBottom: isActive ? '2px solid #3b82f6' : 'none',
                            }}
                            onMouseEnter={(e) => {
                                if (!isActive) {
                                    e.currentTarget.style.background = '#f3f4f6';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isActive) {
                                    e.currentTarget.style.background = 'transparent';
                                }
                            }}
                        >
                            <span>{tab.icon}</span>
                            <span>{tab.label}</span>
                        </button>
                    );
                })}
            </div>

            {/* Main Content Area */}
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
                            onRuleClick={(ruleId) => {
                                setEditingRuleId(ruleId);
                            }}
                        />
                    ) : activeTab === 'exceptions' ? (
                        <ExceptionsTab 
                            discrepancies={discrepancies}
                            ruleViolations={calculatedRulesData?.rules?.filter(r => r.status !== 'PASS') || []}
                        />
                    ) : (
                        <InsightsTab />
                    )}
                </div>
            </div>

            {/* Modals & Panels */}
            {selectedPair && (
                <DocumentPairPanel
                    isOpen={!!selectedPair}
                    onClose={() => setSelectedPair(null)}
                    pair={selectedPair}
                    matches={matches}
                />
            )}

            {editingRule && (
                <EditRuleModal
                    isOpen={!!editingRuleId}
                    onClose={() => setEditingRuleId(null)}
                    rule={editingRule}
                    onSave={handleSaveRule}
                />
            )}

        </div>
    );
}
