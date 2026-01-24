import React, { useEffect, useState } from 'react';
import { 
  DollarSign, 
  ShieldCheck, 
  AlertTriangle, 
  Clock,
  CheckCircle2,
  Loader2
} from 'lucide-react';

import type { ForensicDiscrepancy, DocumentHealthResponse } from '../../../lib/forensic_reconciliation';
import { forensicReconciliationService } from '../../../lib/forensic_reconciliation';

interface OverviewTabProps {
  healthScore: number;
  criticalItems: ForensicDiscrepancy[];
  recentActivity?: any[];
  propertyId?: number;
  periodId?: number;
}

export default function OverviewTab({ healthScore, criticalItems, recentActivity = [], propertyId, periodId }: OverviewTabProps) {
  const [documentHealth, setDocumentHealth] = useState<DocumentHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (propertyId && periodId) {
      loadDocumentHealth();
    }
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
    mortgage_statement: 'Mortgage Statement'
  };

  return (
    <div className="space-y-6">
       
       {/* Top Cards Grid */}
       <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

           {/* Card 2: Critical Reconciliations */}
           <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 md:col-span-2">
               <div className="flex justify-between items-center mb-4">
                   <h3 className="font-bold text-gray-900 flex items-center gap-2">
                       <AlertTriangle className="w-5 h-5 text-amber-500" /> Critical Reconciliations
                   </h3>
                   <button className="text-sm text-blue-600 font-medium hover:underline">View All</button>
               </div>

               <div className="space-y-3">
                   {criticalItems.length > 0 ? criticalItems.map(item => (
                       <div key={item.id} className="flex items-center justify-between p-3 border border-gray-50 rounded-lg hover:bg-gray-50 transition-colors group cursor-pointer">
                           <div className="flex items-center gap-3">
                               <div className={`p-2 rounded-lg ${
                                   item.severity === 'high' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                               }`}>
                                   <DollarSign className="w-5 h-5" />
                               </div>
                               <div>
                                   <h4 className="font-bold text-gray-900 text-sm group-hover:text-blue-700">{item.description}</h4>
                                   <div className="flex items-center gap-2 mt-0.5">
                                      <span className="text-xs text-gray-500 capitalize">{item.discrepancy_type.replace(/_/g, ' ')}</span>
                                   </div>
                               </div>
                           </div>
                           <div className="text-right">
                               <div className="font-bold text-gray-900 text-sm">{item.difference ? `$${item.difference}` : '-'}</div>
                               <div className="text-xs text-amber-600 font-medium whitespace-nowrap">Requires Attention</div>
                           </div>
                       </div>
                   )) : (
                       <div className="text-center py-8 text-gray-400 text-sm">No critical items found</div>
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

    </div>
  );
}
