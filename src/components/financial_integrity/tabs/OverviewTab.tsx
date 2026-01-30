import React, { useEffect, useState, useMemo } from 'react';
import {
  DollarSign,
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Loader2,
  History,
  TrendingDown,
} from 'lucide-react';

import type { ForensicDiscrepancy, DocumentHealthResponse } from '../../../lib/forensic_reconciliation';
import { forensicReconciliationService } from '../../../lib/forensic_reconciliation';
import type { CovenantComplianceHistoryItem } from '../../../lib/covenant_compliance';
import { covenantComplianceService } from '../../../lib/covenant_compliance';
import { varianceAnalysisService, type VarianceAlertItem } from '../../../lib/variance_analysis';

interface PeriodOption {
  id: number;
  period_year?: number;
  period_month?: number;
}

interface OverviewTabProps {
  healthScore: number;
  criticalItems: ForensicDiscrepancy[];
  ruleViolations?: any[];
  recentActivity?: any[];
  propertyId?: number;
  periodId?: number;
  /** Optional list of periods for property; used to show period labels in Covenant History */
  periods?: PeriodOption[];
}

export default function OverviewTab({ healthScore, criticalItems, ruleViolations = [], recentActivity = [], propertyId, periodId, periods = [] }: OverviewTabProps) {
  const [documentHealth, setDocumentHealth] = useState<DocumentHealthResponse | null>(null);
  const [covenantHistory, setCovenantHistory] = useState<CovenantComplianceHistoryItem[]>([]);
  const [covenantHistoryAll, setCovenantHistoryAll] = useState<CovenantComplianceHistoryItem[]>([]);
  const [varianceAlerts, setVarianceAlerts] = useState<VarianceAlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [covenantLoading, setCovenantLoading] = useState(false);
  const [varianceAlertsLoading, setVarianceAlertsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (propertyId && periodId) {
      loadDocumentHealth();
    }
  }, [propertyId, periodId]);

  useEffect(() => {
    if (propertyId && periodId) {
      covenantComplianceService.getComplianceHistory(propertyId, periodId)
        .then(setCovenantHistory)
        .catch(() => setCovenantHistory([]));
    } else {
      setCovenantHistory([]);
    }
  }, [propertyId, periodId]);

  // Covenant compliance history over time (all periods for selected property)
  useEffect(() => {
    if (propertyId) {
      covenantComplianceService.getComplianceHistory(propertyId)
        .then(setCovenantHistoryAll)
        .catch(() => setCovenantHistoryAll([]));
    } else {
      setCovenantHistoryAll([]);
    }
  }, [propertyId]);

  // Variance breach alerts (AUDIT-48)
  useEffect(() => {
    if (!propertyId) {
      setVarianceAlerts([]);
      return;
    }
    setVarianceAlertsLoading(true);
    varianceAnalysisService.getVarianceAlerts({
      property_id: propertyId,
      period_id: periodId ?? undefined,
      limit: 25,
    })
      .then(setVarianceAlerts)
      .catch(() => setVarianceAlerts([]))
      .finally(() => setVarianceAlertsLoading(false));
  }, [propertyId, periodId]);

  const loadDocumentHealth = async () => {
    if (!propertyId || !periodId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await forensicReconciliationService.getDocumentHealth(propertyId, periodId);
      setDocumentHealth(data);
    } catch (err) {
      console.error('Error loading document health:', err);
      setError('Failed to load document health data');
    } finally {
      setLoading(false);
    }
  };
  
  // Mock activity if empty (fallback)
  const activity = recentActivity.length > 0 ? recentActivity : [
    { id: 1, type: 'match', desc: 'Matched 45 items in Balance Sheet', time: '2 mins ago', icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-100' },
    { id: 2, type: 'alert', desc: 'New variance detected in Rent Roll', time: '15 mins ago', icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-100' },
    { id: 3, type: 'system', desc: 'Bank statement parsing completed', time: '1 hour ago', icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100' },
  ];

  // Document type display names
  const documentLabels: Record<string, string> = {
    balance_sheet: 'Balance Sheet',
    income_statement: 'Income Statement',
    cash_flow: 'Cash Flow',
    rent_roll: 'Rent Roll',
    mortgage_statement: 'Mortgage Statement',
    three_statement_integration: 'Three Statement Integration'
  };

  // Combine critical discrepancies and rule violations
  const allCriticalItems = useMemo(() => {
    const items: any[] = [];
    
    // Add forensic discrepancies with severity 'high' or 'critical'
    criticalItems.forEach(d => {
      items.push({
        id: `disc-${d.id}`,
        type: 'discrepancy',
        severity: d.severity,
        description: d.description || 'Discrepancy Detected',
        discrepancy_type: d.discrepancy_type || 'unknown',
        difference: d.difference || d.amount_difference,
        source: 'Cross-Document Match'
      });
    });
    
    // Add critical/high rule violations
    ruleViolations
      .filter(rule => {
        const ruleId = rule.rule_id?.toUpperCase() || '';
        // Include accounting equations, large variances, and critical ratios
        return (
          ruleId.includes('BS-1') || // Accounting Equation
          ruleId.includes('IS-1') || // Net Income
          ruleId.includes('LIQUIDITY') ||
          ruleId.includes('WORKING') ||
          (rule.actual_value && rule.expected_value && 
           Math.abs(parseFloat(rule.actual_value) - parseFloat(rule.expected_value)) > 100000)
        );
      })
      .slice(0, 10) // Limit to top 10 critical rules
      .forEach(rule => {
        const variance = rule.actual_value && rule.expected_value
          ? Math.abs(parseFloat(rule.actual_value) - parseFloat(rule.expected_value))
          : 0;
        
        items.push({
          id: `rule-${rule.rule_id}`,
          type: 'rule_violation',
          severity: 'high',
          description: `${rule.rule_name} (${rule.rule_id})`,
          discrepancy_type: 'validation_failure',
          difference: variance,
          source: 'Rule Validation',
          rule_data: rule
        });
      });
    
    // Sort by difference amount (largest first)
    return items.sort((a, b) => (b.difference || 0) - (a.difference || 0));
  }, [criticalItems, ruleViolations]);

  return (
    <div className="space-y-6">
       
       {/* Top Cards Grid */}
       <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
           {/* Card 1: Document Health */}
           <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
               <div className="flex justify-between items-center mb-4">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <ShieldCheck className="w-5 h-5 text-blue-600" /> Document Health
                   </h3>
                   <span className="text-xs font-medium px-2 py-1 bg-gray-100 rounded-lg text-gray-600">
                       Overall: {documentHealth ? documentHealth.overall_health.toFixed(2) : healthScore}%
                   </span>
               </div>
               
               {loading ? (
                   <div className="flex items-center justify-center py-8">
                       <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                   </div>
               ) : error ? (
                   <div className="text-center py-4 text-red-600 text-sm">{error}</div>
               ) : documentHealth ? (
                   <div className="space-y-3">
                       {Object.entries(documentHealth.documents).map(([docType, health]) => (
                           <div key={docType}>
                               <div className="flex justify-between text-sm mb-1">
                                   <span className="text-gray-600 font-medium">{documentLabels[docType]}</span>
                                   <div className="flex items-center gap-2">
                                       <span className={`font-bold ${health.health_score < 90 ? 'text-amber-600' : 'text-gray-900'}`}>
                                           {health.health_score.toFixed(1)}%
                                       </span>
                                       <span className="text-xs text-gray-400">
                                           ({health.passed_rules}/{health.total_rules})
                                       </span>
                                   </div>
                               </div>
                               <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                   <div 
                                       className={`h-full rounded-full transition-all ${
                                           health.total_rules === 0 ? 'bg-gray-300' :
                                           health.health_score === 100 ? 'bg-green-500' : 
                                           health.health_score >= 90 ? 'bg-blue-500' : 
                                           health.health_score >= 70 ? 'bg-amber-500' : 'bg-red-500'
                                       }`} 
                                       style={{ width: `${health.total_rules === 0 ? 0 : health.health_score}%` }}
                                   />
                               </div>
                           </div>
                       ))}
                   </div>
               ) : (
                   <div className="text-center py-4 text-gray-500 text-sm">No data available</div>
               )}
           </div>

           {/* Covenant Compliance */}
           <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
               <div className="flex justify-between items-center mb-4">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <ShieldCheck className="w-5 h-5 text-emerald-600" /> Covenant Compliance
                   </h3>
                   <span className="text-xs font-medium px-2 py-1 bg-gray-100 rounded-lg text-gray-600">
                       {covenantHistory.filter(c => c.is_compliant).length}/{covenantHistory.length} compliant
                   </span>
               </div>
               {covenantHistory.length === 0 ? (
                   <div className="text-center py-4 text-gray-500 text-sm">Run reconciliation to see covenant history</div>
               ) : (
                   <div className="space-y-2 max-h-40 overflow-y-auto">
                       {covenantHistory.map(c => (
                           <div key={c.id} className="flex justify-between items-center text-sm py-1 border-b border-gray-50 last:border-0">
                               <span className="text-gray-700 font-medium">{c.covenant_type}</span>
                               <span className={c.is_compliant ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
                                   {c.is_compliant ? 'Pass' : 'Fail'}
                               </span>
                           </div>
                       ))}
                   </div>
               )}
           </div>

           {/* Card 2: Critical Reconciliations */}
           <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 md:col-span-2">
               <div className="flex justify-between items-center mb-4">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <AlertTriangle className="w-5 h-5 text-amber-500" /> Critical Issues
                   </h3>
                   <button 
                       onClick={() => {
                           // Navigate to exceptions tab
                           const event = new CustomEvent('switchTab', { detail: 'exceptions' });
                           window.dispatchEvent(event);
                       }}
                       className="text-sm text-blue-600 font-medium hover:underline"
                   >
                       View All
                   </button>
               </div>

               <div className="space-y-3 max-h-96 overflow-y-auto">
                   {allCriticalItems.length > 0 ? allCriticalItems.map(item => (
                       <div 
                           key={item.id} 
                           onClick={() => {
                               if (item.type === 'rule_violation' && item.rule_data?.rule_id) {
                                   window.location.hash = `rule-configuration/${item.rule_data.rule_id}`;
                               }
                           }}
                           className="flex items-center justify-between p-3 border border-gray-50 rounded-lg hover:bg-gray-50 transition-colors group cursor-pointer"
                       >
                           <div className="flex items-center gap-3">
                               <div className={`p-2 rounded-lg ${
                                   item.severity === 'critical' || item.severity === 'high' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                               }`}>
                                   <DollarSign className="w-5 h-5" />
                               </div>
                               <div>
                                   <div className="flex items-center gap-2">
                                       <h4 className="font-bold text-gray-900 text-sm group-hover:text-blue-700">{item.description}</h4>
                                       <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                           item.type === 'rule_violation' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                                       }`}>
                                           {item.type === 'rule_violation' ? 'RULE' : 'MATCH'}
                                       </span>
                                   </div>
                                   <div className="flex items-center gap-2 mt-0.5">
                                      <span className="text-xs text-gray-500 capitalize">{item.source}</span>
                                   </div>
                               </div>
                           </div>
                           <div className="text-right">
                               <div className="font-bold text-gray-900 text-sm">
                                   {item.difference ? `$${typeof item.difference === 'number' 
                                       ? item.difference.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                       : item.difference}` : '-'}
                               </div>
                               <div className="text-xs text-red-600 font-medium whitespace-nowrap">
                                   {item.type === 'rule_violation' ? 'Review Rule' : 'Requires Attention'}
                               </div>
                           </div>
                       </div>
                   )) : (
                       <div className="text-center py-8">
                           <div className="text-gray-400 text-sm mb-1">✅ No critical issues</div>
                           <div className="text-xs text-gray-500">All validations passing!</div>
                       </div>
                   )}
               </div>
           </div>
       </div>

       {/* Recent Activity */}
       <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
           <div className="px-5 py-4 border-b border-gray-50 flex justify-between items-center">
               <h3 className="font-bold text-gray-900 flex items-center gap-2">
                   <Clock className="w-5 h-5 text-gray-400" /> Recent Activity
               </h3>
           </div>
           <div className="divide-y divide-gray-50">
               {activity.map((item) => (
                   <div key={item.id} className="p-4 flex gap-4 hover:bg-gray-50 transition-colors">
                       <div className={`mt-1 p-2 rounded-full ${item.bg} ${item.color}`}>
                           <item.icon className="w-4 h-4" />
                       </div>
                       <div>
                           <p className="text-sm font-medium text-gray-900">{item.desc}</p>
                           <p className="text-xs text-gray-500 mt-0.5">{item.time}</p>
                       </div>
                   </div>
               ))}
           </div>
       </div>

       {/* Covenant History Over Time & Variance Alerts */}
       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
           {/* Covenant History (all periods) */}
           <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
               <div className="px-5 py-4 border-b border-gray-50 flex justify-between items-center">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <History className="w-5 h-5 text-emerald-600" /> Covenant History
                   </h3>
                   <div className="flex items-center gap-2">
                       {propertyId && (
                           <span className="text-xs text-gray-500">
                               {covenantHistoryAll.length} record{covenantHistoryAll.length !== 1 ? 's' : ''}
                           </span>
                       )}
                       {propertyId && (
                           <button
                               type="button"
                               onClick={() => { window.location.hash = 'covenant-compliance'; }}
                               className="text-sm text-blue-600 font-medium hover:underline"
                           >
                               View in Covenant Compliance
                           </button>
                       )}
                   </div>
               </div>
               <div className="overflow-x-auto max-h-64 overflow-y-auto">
                   {!propertyId ? (
                       <div className="p-4 text-center text-gray-500 text-sm">Select a property to view covenant history</div>
                   ) : covenantHistoryAll.length === 0 ? (
                       <div className="p-4 text-center text-gray-500 text-sm">Run reconciliation to populate covenant history</div>
                   ) : (
                       <table className="w-full text-sm">
                           <thead className="bg-gray-50 sticky top-0">
                               <tr>
                                   <th className="text-left px-3 py-2 font-medium text-gray-700">Period</th>
                                   <th className="text-left px-3 py-2 font-medium text-gray-700">Type</th>
                                   <th className="text-right px-3 py-2 font-medium text-gray-700">Value</th>
                                   <th className="text-right px-3 py-2 font-medium text-gray-700">Threshold</th>
                                   <th className="text-center px-3 py-2 font-medium text-gray-700">Status</th>
                               </tr>
                           </thead>
                           <tbody className="divide-y divide-gray-50">
                               {covenantHistoryAll
                                   .sort((a, b) => (b.period_id ?? 0) - (a.period_id ?? 0))
                                   .slice(0, 50)
                                   .map((row) => {
                                     const period = periods.find((p) => p.id === row.period_id);
                                     const periodLabel = period?.period_year != null && period?.period_month != null
                                       ? `${period.period_year}-${String(period.period_month).padStart(2, '0')}`
                                       : String(row.period_id);
                                     return (
                                       <tr key={row.id} className="hover:bg-gray-50">
                                           <td className="px-3 py-2 text-gray-600">{periodLabel}</td>
                                           <td className="px-3 py-2 font-medium text-gray-800">{row.covenant_type}</td>
                                           <td className="px-3 py-2 text-right text-gray-700">
                                               {row.calculated_value != null ? row.calculated_value.toFixed(2) : '—'}
                                           </td>
                                           <td className="px-3 py-2 text-right text-gray-600">
                                               {row.threshold_value != null ? row.threshold_value.toFixed(2) : '—'}
                                           </td>
                                           <td className="px-3 py-2 text-center">
                                               <span className={row.is_compliant ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
                                                   {row.is_compliant ? 'Pass' : 'Fail'}
                                               </span>
                                           </td>
                                       </tr>
                                   );
                                   })}
                           </tbody>
                       </table>
                   )}
               </div>
               {propertyId && (
                   <p className="px-5 py-2 text-xs text-gray-400 border-t border-gray-50">
                       Tip:{' '}
                       <button
                           type="button"
                           onClick={() => window.dispatchEvent(new CustomEvent('navigateToPage', { detail: { page: 'reports', hash: 'statements' } }))}
                           className="text-blue-500 hover:underline font-medium"
                       >
                           Recalculate metrics
                       </button>
                       {' '}in Financials → Statements to refresh covenant and analytics data.
                   </p>
               )}
           </div>

           {/* Variance Alerts (AUDIT-48) */}
           <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
               <div className="px-5 py-4 border-b border-gray-50 flex justify-between items-center">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <TrendingDown className="w-5 h-5 text-amber-500" /> Variance Alerts
                   </h3>
                   <div className="flex items-center gap-2">
                       {propertyId && varianceAlerts.length > 0 && (
                           <span className="text-xs font-medium text-amber-600">{varianceAlerts.length} alert{varianceAlerts.length !== 1 ? 's' : ''}</span>
                       )}
                       <button
                           type="button"
                           onClick={() => window.dispatchEvent(new CustomEvent('navigateToPage', { detail: { page: 'risk' } }))}
                           className="text-sm text-blue-600 font-medium hover:underline"
                       >
                           View all
                       </button>
                   </div>
               </div>
               <div className="overflow-y-auto max-h-64">
                   {!propertyId ? (
                       <div className="p-4 text-center text-gray-500 text-sm">Select a property to view variance alerts</div>
                   ) : varianceAlertsLoading ? (
                       <div className="flex items-center justify-center py-8">
                           <Loader2 className="w-6 h-6 animate-spin text-amber-600" />
                       </div>
                   ) : varianceAlerts.length === 0 ? (
                       <div className="p-4 text-center text-gray-500 text-sm">No variance breach alerts for this property</div>
                   ) : (
                       <ul className="divide-y divide-gray-50">
                           {varianceAlerts.map((alert) => (
                               <li key={alert.id} className="p-4 hover:bg-gray-50">
                                   <div className="flex justify-between items-start gap-2">
                                       <div>
                                           <p className="text-sm font-medium text-gray-900">
                                               {alert.message || alert.related_metric || 'Variance breach'}
                                           </p>
                                           <p className="text-xs text-gray-500 mt-0.5">
                                               {alert.period_year != null && alert.period_month != null
                                                   ? `${alert.period_year}-${String(alert.period_month).padStart(2, '0')}`
                                                   : '—'}
                                               {alert.property_code ? ` · ${alert.property_code}` : ''}
                                           </p>
                                       </div>
                                       <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                           alert.severity === 'CRITICAL' || alert.severity === 'URGENT'
                                               ? 'bg-red-100 text-red-700'
                                               : alert.severity === 'WARNING'
                                               ? 'bg-amber-100 text-amber-700'
                                               : 'bg-gray-100 text-gray-700'
                                       }`}>
                                           {alert.severity}
                                       </span>
                                   </div>
                                   <p className="text-xs text-gray-500 mt-1">{alert.status}</p>
                               </li>
                           ))}
                       </ul>
                   )}
               </div>
           </div>
       </div>

    </div>
  );
}
