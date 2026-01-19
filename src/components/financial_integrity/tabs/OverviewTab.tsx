import React from 'react';
import { 
  DollarSign, 
  ShieldCheck, 
  AlertTriangle, 
  Clock,
  CheckCircle2
} from 'lucide-react';

import type { ForensicDiscrepancy } from '../../../lib/forensic_reconciliation';

interface OverviewTabProps {
  healthScore: number;
  criticalItems: ForensicDiscrepancy[];
  recentActivity?: any[];
}

export default function OverviewTab({ healthScore, criticalItems, recentActivity = [] }: OverviewTabProps) {
  
  // Mock activity if empty (fallback)
  const activity = recentActivity.length > 0 ? recentActivity : [
    { id: 1, type: 'match', desc: 'Matched 45 items in Balance Sheet', time: '2 mins ago', icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-100' },
    { id: 2, type: 'alert', desc: 'New variance detected in Rent Roll', time: '15 mins ago', icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-100' },
    { id: 3, type: 'system', desc: 'Bank statement parsing completed', time: '1 hour ago', icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100' },
  ];

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
                       Overall: {healthScore}%
                   </span>
               </div>
               
               <div className="space-y-3">
                   {[
                       { label: 'Balance Sheet', score: healthScore > 0 ? Math.min(100, healthScore + 5) : 98, rules: 12 },
                       { label: 'Income Statement', score: healthScore > 0 ? Math.max(0, healthScore - 5) : 92, rules: 8 },
                       { label: 'Rent Roll', score: 85, rules: 15 },
                       { label: 'Bank Statements', score: 100, rules: 4 },
                   ].map((item) => (
                       <div key={item.label}>
                           <div className="flex justify-between text-sm mb-1">
                               <span className="text-gray-600 font-medium">{item.label}</span>
                               <span className={`font-bold ${item.score < 90 ? 'text-amber-600' : 'text-gray-900'}`}>{item.score}%</span>
                           </div>
                           <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                               <div 
                                   className={`h-full rounded-full ${
                                       item.score === 100 ? 'bg-green-500' : 
                                       item.score > 90 ? 'bg-blue-500' : 'bg-amber-500'
                                   }`} 
                                   style={{ width: `${item.score}%` }}
                               />
                           </div>
                       </div>
                   ))}
               </div>
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
