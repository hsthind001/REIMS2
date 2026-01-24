
import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  History, 
  Calculator, 
  ArrowRight,
  FileText,
  User,
  ArrowLeft
} from 'lucide-react';
import { Button } from '../components/design-system';

export default function RuleConfigurationPage() {
  const [ruleId, setRuleId] = useState<string>('');

  useEffect(() => {
    // Parse rule ID from hash: #rule-configuration/R-101
    const hash = window.location.hash;
    const parts = hash.split('/');
    if (parts.length > 1) {
      setRuleId(parts[1]);
    }
  }, []);

  const handleBack = () => {
    window.location.hash = 'forensic-reconciliation';
  };

  // Mock data - same as RuleDetailModal for now
  const ruleDetails = {
    id: ruleId || 'R-101',
    name: 'Bank Account Reconciliation',
    description: 'Validates that the Balance Sheet cash account matches the ending balance on the monthly Bank Statement.',
    formula: 'ABS(BalanceSheet.Cash - BankStatement.EndingBalance) < 0.01',
    status: 'pass',
    type: 'Direct Match',
    lastRun: 'Oct 24, 2025 14:30:22',
    variance: 0,
    threshold: 0.01,
    sourceData: {
      account: 'Balance Sheet: 1000-Cash',
      value: '$1,245,678.45',
      date: '2025-10-31'
    },
    targetData: {
      account: 'Bank Stmt: Chase-8892',
      value: '$1,245,678.45',
      date: '2025-10-31'
    },
    history: [
      { date: 'Oct 2025', status: 'pass', variance: 0 },
      { date: 'Sep 2025', status: 'pass', variance: 0 },
      { date: 'Aug 2025', status: 'warn', variance: 150.00 },
      { date: 'Jul 2025', status: 'pass', variance: 0 },
    ]
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation Header */}
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            onClick={handleBack}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Hub
          </Button>
          <div className="h-6 w-px bg-gray-300" />
          <h1 className="text-xl font-bold text-gray-900">Rule Configuration</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="px-6 py-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
            <div>
              <div className="flex items-center gap-2 mb-2">
                 <span className="text-xs font-mono font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded">
                   {ruleDetails.id}
                 </span>
                 <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full uppercase tracking-wide">
                   {ruleDetails.type}
                 </span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">{ruleDetails.name}</h2>
            </div>
            {/* Status Badge */}
            <div className={`px-4 py-2 rounded-lg border flex items-center gap-2 ${
                ruleDetails.status === 'pass' 
                ? 'bg-green-50 border-green-100 text-green-700' 
                : 'bg-amber-50 border-amber-100 text-amber-700'
            }`}>
                {ruleDetails.status === 'pass' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                <span className="font-bold">{ruleDetails.status === 'pass' ? 'Passing' : 'Failing'}</span>
            </div>
          </div>

          {/* Content */}
          <div className="p-8 space-y-8">
              
              {/* Formula & Logic */}
              <div>
                 <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">
                    <Calculator className="w-4 h-4 text-gray-400" /> Validation Logic
                 </h4>
                 <div className="bg-gray-900 rounded-lg p-6 font-mono text-sm text-gray-300 shadow-inner">
                    <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
                       <span className="text-gray-500 font-sans">Formula Definition</span>
                       <span className="text-xs text-gray-500 font-sans bg-gray-800 px-2 py-1 rounded">Threshold: {ruleDetails.threshold}</span>
                    </div>
                    <code className="text-blue-300 text-base">{ruleDetails.formula}</code>
                 </div>
                 <p className="text-base text-gray-600 mt-4 leading-relaxed max-w-2xl">
                    {ruleDetails.description}
                 </p>
              </div>

              <div className="h-px bg-gray-100" />

              {/* Comparison Data */}
              <div>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">
                    <FileText className="w-4 h-4 text-gray-400" /> Current Evaluation values
                 </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center relative">
                       {/* Arrow for large screens */}
                       <div className="hidden md:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-white p-1.5 rounded-full border border-gray-200 shadow-sm text-gray-400">
                          <ArrowRight className="w-5 h-5" />
                       </div>

                       {/* Source */}
                       <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-200 transition-colors">
                          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Source A</div>
                          <div className="flex items-center gap-2 mb-4">
                              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                                <FileText className="w-5 h-5" />
                              </div>
                              <span className="font-bold text-gray-900 text-lg">Balance Sheet</span>
                          </div>
                          <div className="space-y-2">
                              <div className="text-sm text-gray-500 flex justify-between">
                                <span>Account</span>
                                <span className="font-mono text-gray-700">1000-Cash</span>
                              </div>
                              <div className="text-3xl font-bold text-gray-900 tracking-tight">{ruleDetails.sourceData.value}</div>
                              <div className="text-xs text-gray-400">As of {ruleDetails.sourceData.date}</div>
                          </div>
                       </div>

                       {/* Target */}
                       <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-purple-200 transition-colors">
                          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Source B</div>
                          <div className="flex items-center gap-2 mb-4">
                              <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
                                <FileText className="w-5 h-5" />
                              </div>
                              <span className="font-bold text-gray-900 text-lg">Bank Statement</span>
                          </div>
                          <div className="space-y-2">
                              <div className="text-sm text-gray-500 flex justify-between">
                                <span>Statement</span>
                                <span className="font-mono text-gray-700">Chase-8892</span>
                              </div>
                              <div className="text-3xl font-bold text-gray-900 tracking-tight">{ruleDetails.targetData.value}</div>
                              <div className="text-xs text-gray-400">As of {ruleDetails.targetData.date}</div>
                          </div>
                       </div>
                  </div>
              </div>

              <div className="h-px bg-gray-100" />

              {/* History */}
               <div>
                 <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">
                    <History className="w-4 h-4 text-gray-400" /> Execution History
                 </h4>
                 <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                     <table className="w-full text-sm text-left">
                         <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
                             <tr>
                                 <th className="px-6 py-3 font-medium">Period</th>
                                 <th className="px-6 py-3 font-medium">Status</th>
                                 <th className="px-6 py-3 font-medium text-right">Variance</th>
                             </tr>
                         </thead>
                         <tbody className="divide-y divide-gray-100">
                             {ruleDetails.history.map((h, i) => (
                                 <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                                     <td className="px-6 py-4 text-gray-900 font-medium">{h.date}</td>
                                     <td className="px-6 py-4">
                                         <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                                             h.status === 'pass' 
                                             ? 'bg-green-100 text-green-700' 
                                             : 'bg-amber-100 text-amber-700'
                                         }`}>
                                             {h.status === 'pass' ? 'Pass' : 'Warning'}
                                         </span>
                                     </td>
                                     <td className="px-6 py-4 text-right font-mono text-gray-600">
                                         {h.variance === 0 ? '-' : `$${h.variance.toFixed(2)}`}
                                     </td>
                                 </tr>
                             ))}
                         </tbody>
                     </table>
                 </div>
              </div>

          </div>

          {/* Footer */}
          <div className="px-8 py-6 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
             <div className="flex items-center gap-3">
                <div className="flex -space-x-2">
                   <div className="w-8 h-8 rounded-full bg-blue-100 border-2 border-white flex items-center justify-center text-xs font-bold text-blue-700">JS</div>
                   <div className="w-8 h-8 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
                      <User className="w-4 h-4 text-gray-400" />
                   </div>
                </div>
                <div>
                   <div className="text-sm font-medium text-gray-900">Maintained by Finance Team</div>
                   <div className="text-xs text-gray-500">Last updated: {ruleDetails.lastRun}</div>
                </div>
             </div>
             
             <div className="flex gap-3">
                 <Button variant="secondary">
                     Edit Logic
                 </Button>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
