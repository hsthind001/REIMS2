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
  // State for filtering
  const [statusFilter, setStatusFilter] = useState<'all' | 'passed' | 'variance'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Calculate statistics
  const stats = {
    total: rules.length,
    passed: rules.filter(r => r.status === 'PASS').length,
    variance: rules.filter(r => r.status !== 'PASS').length,
    passRate: rules.length > 0 ? Math.round((rules.filter(r => r.status === 'PASS').length / rules.length) * 100) : 0
  };

  // Filter logic
  const filteredRules = rules.filter(rule => {
      // Apply status filter
      let matchesStatus = true;
      if (statusFilter === 'passed') {
        matchesStatus = rule.status === 'PASS';
      } else if (statusFilter === 'variance') {
        matchesStatus = rule.status !== 'PASS';
      }
      
      // Apply search filter
      const name = rule.rule_name || '';
      const desc = rule.description || '';
      const matchesSearch = name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            desc.toLowerCase().includes(searchQuery.toLowerCase());
      
      return matchesStatus && matchesSearch;
  });

  // Click handlers for filter cards
  const handleFilterClick = (filter: 'all' | 'passed' | 'variance') => {
    // Toggle: if clicking the same filter, reset to 'all'
    setStatusFilter(statusFilter === filter ? 'all' : filter);
  };

  return (
    <div className="space-y-6">
       {/* Summary Statistics */}
       <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
           {/* Total Rules */}
           <div 
               onClick={() => handleFilterClick('all')}
               className={`bg-gradient-to-br from-blue-50 to-blue-100 border rounded-xl p-4 cursor-pointer transition-all hover:shadow-lg ${
                   statusFilter === 'all' 
                       ? 'border-blue-500 border-2 shadow-lg ring-2 ring-blue-200' 
                       : 'border-blue-200 hover:border-blue-300'
               }`}
           >
               <div className="flex items-center justify-between">
                   <div>
                       <p className="text-sm font-medium text-blue-700 mb-1">Total Rules</p>
                       <p className="text-3xl font-bold text-blue-900">{stats.total}</p>
                       {statusFilter === 'all' && (
                           <p className="text-xs text-blue-600 mt-1 font-medium">Showing all</p>
                       )}
                   </div>
                   <div className="p-3 bg-blue-200 rounded-lg">
                       <Calculator className="w-6 h-6 text-blue-700" />
                   </div>
               </div>
           </div>

           {/* Passed Rules */}
           <div 
               onClick={() => handleFilterClick('passed')}
               className={`bg-gradient-to-br from-green-50 to-green-100 border rounded-xl p-4 cursor-pointer transition-all hover:shadow-lg ${
                   statusFilter === 'passed' 
                       ? 'border-green-500 border-2 shadow-lg ring-2 ring-green-200' 
                       : 'border-green-200 hover:border-green-300'
               }`}
           >
               <div className="flex items-center justify-between">
                   <div>
                       <p className="text-sm font-medium text-green-700 mb-1">Passed</p>
                       <p className="text-3xl font-bold text-green-900">{stats.passed}</p>
                       {statusFilter === 'passed' && (
                           <p className="text-xs text-green-600 mt-1 font-medium">Filtered</p>
                       )}
                   </div>
                   <div className="p-3 bg-green-200 rounded-lg">
                       <CheckCircle2 className="w-6 h-6 text-green-700" />
                   </div>
               </div>
           </div>

           {/* Variance Rules */}
           <div 
               onClick={() => handleFilterClick('variance')}
               className={`bg-gradient-to-br from-amber-50 to-amber-100 border rounded-xl p-4 cursor-pointer transition-all hover:shadow-lg ${
                   statusFilter === 'variance' 
                       ? 'border-amber-500 border-2 shadow-lg ring-2 ring-amber-200' 
                       : 'border-amber-200 hover:border-amber-300'
               }`}
           >
               <div className="flex items-center justify-between">
                   <div>
                       <p className="text-sm font-medium text-amber-700 mb-1">Variance</p>
                       <p className="text-3xl font-bold text-amber-900">{stats.variance}</p>
                       {statusFilter === 'variance' && (
                           <p className="text-xs text-amber-600 mt-1 font-medium">Filtered</p>
                       )}
                   </div>
                   <div className="p-3 bg-amber-200 rounded-lg">
                       <AlertTriangle className="w-6 h-6 text-amber-700" />
                   </div>
               </div>
           </div>

           {/* Pass Rate */}
           <div className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-xl p-4">
               <div className="flex items-center justify-between">
                   <div>
                       <p className="text-sm font-medium text-purple-700 mb-1">Pass Rate</p>
                       <p className="text-3xl font-bold text-purple-900">{stats.passRate}%</p>
                   </div>
                   <div className="p-3 bg-purple-200 rounded-lg">
                       <CheckCircle2 className="w-6 h-6 text-purple-700" />
                   </div>
               </div>
           </div>
       </div>

       {/* Toolbar */}
       <div className="flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center">
           {/* Filter Status */}
           <div className="flex items-center gap-3">
               {statusFilter !== 'all' && (
                   <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-lg">
                       <span className="text-sm text-blue-700">
                           Showing: <strong>{statusFilter === 'passed' ? 'Passed' : 'Variance'} Rules</strong>
                       </span>
                       <button 
                           onClick={() => setStatusFilter('all')}
                           className="text-blue-600 hover:text-blue-800 font-medium text-sm underline"
                       >
                           Clear Filter
                       </button>
                   </div>
               )}
               <span className="text-sm text-gray-600">
                   {filteredRules.length} of {stats.total} rules
               </span>
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
                <div className="text-center py-10">
                    <div className="text-gray-400 mb-2">
                        {searchQuery ? 'No rules match your search.' : 
                         statusFilter === 'passed' ? 'No passed rules found.' :
                         statusFilter === 'variance' ? 'No variance rules found.' :
                         'No rules found for this selection.'}
                    </div>
                    {(searchQuery || statusFilter !== 'all') && (
                        <button 
                            onClick={() => {
                                setSearchQuery('');
                                setStatusFilter('all');
                            }}
                            className="text-sm text-blue-600 hover:underline font-medium"
                        >
                            Clear all filters
                        </button>
                    )}
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
