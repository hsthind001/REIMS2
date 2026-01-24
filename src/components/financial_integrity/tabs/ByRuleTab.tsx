import React, { useState } from 'react';
import { 
  Search, 
  Calculator, 
  CheckCircle2, 
  AlertTriangle,
  ArrowRight
} from 'lucide-react';
import type { CalculatedRuleEvaluation } from '../../../lib/forensic_reconciliation';

interface ByRuleTabProps {
  rules?: CalculatedRuleEvaluation[];
  onRuleClick?: (ruleId: string) => void;
}

export default function ByRuleTab({ rules = [], onRuleClick }: ByRuleTabProps) {
  // ... (state remains)
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // ... (filter logic remains)
  const filteredRules = rules.filter(rule => {
      // type property isn't on CalculatedRuleEvaluation, assume 'derived' or fallback
      const matchesFilter = activeFilter === 'all'; 
      const name = rule.rule_name || '';
      const desc = rule.description || '';
      const matchesSearch = name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            desc.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
       {/* ... (Toolbar remains) */}
       <div className="flex flex-col sm:flex-row justify-between gap-4">
           {/* Filters - Simplified since we don't have types yet */}
           <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
               {/* Hidden for now until we have types */}
           </div>

           {/* Search */}
           <div className="relative">
               <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
               <input 
                   type="text" 
                   placeholder="Search rules..." 
                   className="pl-9 pr-4 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-64"
                   value={searchQuery}
                   onChange={(e) => setSearchQuery(e.target.value)}
               />
           </div>
       </div>

       {/* Rules List */}
       <div className="grid grid-cols-1 gap-4">
           {filteredRules.length === 0 && (
                <div className="text-center py-10 text-gray-400">
                    No rules found for this selection.
                </div>
           )}
           {filteredRules.map(rule => (
               <div key={rule.rule_id} className="bg-white border border-gray-100 rounded-xl p-5 hover:border-blue-100 transition-colors shadow-sm group">
                   <div className="flex justify-between items-start">
                       <div className="flex gap-4">
                           <div className={`mt-1 p-2 rounded-lg ${
                               rule.status === 'PASS' ? 'bg-green-50 text-green-600' : 'bg-amber-50 text-amber-600'
                           }`}>
                               <Calculator className="w-4 h-4" />
                           </div>
                           
                           <div>
                               <div className="flex items-center gap-2 mb-1">
                                   <h4 className="font-bold text-gray-900">{rule.rule_name}</h4>
                                   <span className="text-xs font-medium text-gray-400 border border-gray-100 px-1.5 rounded">
                                       {rule.rule_id}
                                   </span>
                               </div>
                               <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                               <div className="flex items-center gap-2">
                                   <code className="text-xs bg-gray-50 text-gray-500 px-2 py-1 rounded border border-gray-100 font-mono">
                                       {rule.formula}
                                   </code>
                               </div>
                           </div>
                       </div>

                       <div className="flex flex-col items-end gap-2">
                           {rule.status === 'PASS' ? (
                               <div className="flex items-center gap-1.5 text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded-full">
                                   <CheckCircle2 className="w-4 h-4" /> Passed
                               </div>
                           ) : (
                               <div className="flex items-center gap-1.5 text-sm font-bold text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
                                   <AlertTriangle className="w-4 h-4" /> Variance
                               </div>
                           )}
                           <span className="text-xs text-gray-400">Expected: {rule.expected_value} | Actual: {rule.actual_value}</span>
                       </div>
                   </div>

                   <div className="mt-4 pt-4 border-t border-gray-50 flex justify-between items-center">
                       <div className="flex gap-2">
                            {/* Tags would go here if we had docTypes */}
                       </div>
                       
                      <button 
                           onClick={() => {
                               // Navigate to dedicated rule configuration page
                               window.location.hash = `rule-configuration/${rule.rule_id}`;
                           }}
                           className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-auto"
                      >
                          Configure Rule <ArrowRight className="w-4 h-4" />
                      </button>
                   </div>
               </div>
           ))}
       </div>
    </div>
  );
}
