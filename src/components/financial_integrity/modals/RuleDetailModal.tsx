import React from 'react';
import { 
  X, 
  CheckCircle2, 
  AlertTriangle, 
  History, 
  Calculator, 
  ArrowRight,
  FileText,
  User
} from 'lucide-react';

interface RuleDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  ruleId: string;
}

export default function RuleDetailModal({ isOpen, onClose, ruleId }: RuleDetailModalProps) {
  if (!isOpen) return null;

  // Mock data for the modal - will be replaced with real data fetch
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
          <div>
            <div className="flex items-center gap-2 mb-1">
               <span className="text-xs font-mono font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded">
                 {ruleDetails.id}
               </span>
               <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full uppercase tracking-wide">
                 {ruleDetails.type}
               </span>
            </div>
            <h3 className="text-lg font-bold text-gray-900">{ruleDetails.name}</h3>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
            
            {/* Status Section */}
            <div className={`rounded-xl p-5 border ${
                ruleDetails.status === 'pass' 
                ? 'bg-green-50/50 border-green-100' 
                : 'bg-amber-50/50 border-amber-100'
            }`}>
               <div className="flex items-start justify-between">
                  <div className="flex gap-3">
                     <div className={`mt-1 p-1.5 rounded-full ${
                         ruleDetails.status === 'pass' ? 'bg-green-100 text-green-600' : 'bg-amber-100 text-amber-600'
                     }`}>
                        {ruleDetails.status === 'pass' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                     </div>
                     <div>
                        <h4 className={`font-bold ${
                            ruleDetails.status === 'pass' ? 'text-green-800' : 'text-amber-800'
                        }`}>
                            Validation {ruleDetails.status === 'pass' ? 'Successful' : 'Failed'}
                        </h4>
                        <p className={`text-sm mt-1 ${
                            ruleDetails.status === 'pass' ? 'text-green-700' : 'text-amber-700'
                        }`}>
                           {ruleDetails.status === 'pass' 
                                ? 'Values align perfectly within the defined threshold.' 
                                : `Variance of $${ruleDetails.variance} detected.`
                           }
                        </p>
                     </div>
                  </div>
                  <div className="text-right">
                     <div className="text-sm text-gray-500 mb-0.5">Automated Check</div>
                     <div className="text-xs font-mono text-gray-400">{ruleDetails.lastRun}</div>
                  </div>
               </div>
            </div>

            {/* Formula & Logic */}
            <div>
               <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">
                  <Calculator className="w-4 h-4 text-gray-400" /> Validation Logic
               </h4>
               <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 shadow-inner">
                  <div className="flex justify-between items-center mb-2 border-b border-gray-700 pb-2">
                     <span className="text-gray-500">Formula</span>
                     <span className="text-xs text-gray-500">Threshold: {ruleDetails.threshold}</span>
                  </div>
                  <code className="text-blue-300">{ruleDetails.formula}</code>
               </div>
               <p className="text-sm text-gray-600 mt-3 leading-relaxed">
                  {ruleDetails.description}
               </p>
            </div>

            {/* Comparison Data */}
            <div className="grid grid-cols-2 gap-8 items-center relative">
                 <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-white p-1 rounded-full border border-gray-100 shadow-sm">
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                 </div>

                 {/* Source */}
                 <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Source A</div>
                    <div className="flex items-center gap-2 mb-3">
                        <FileText className="w-4 h-4 text-blue-600" />
                        <span className="font-semibold text-gray-900 text-sm">Balance Sheet</span>
                    </div>
                    <div className="space-y-1">
                        <div className="text-xs text-gray-500">Account: 1000-Cash</div>
                        <div className="text-xl font-bold text-gray-900">{ruleDetails.sourceData.value}</div>
                        <div className="text-xs text-gray-400">As of {ruleDetails.sourceData.date}</div>
                    </div>
                 </div>

                 {/* Target */}
                 <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Source B</div>
                    <div className="flex items-center gap-2 mb-3">
                        <FileText className="w-4 h-4 text-purple-600" />
                        <span className="font-semibold text-gray-900 text-sm">Bank Statement</span>
                    </div>
                    <div className="space-y-1">
                        <div className="text-xs text-gray-500">Stmt: Chase-8892</div>
                        <div className="text-xl font-bold text-gray-900">{ruleDetails.targetData.value}</div>
                        <div className="text-xs text-gray-400">As of {ruleDetails.targetData.date}</div>
                    </div>
                 </div>
            </div>

            {/* History */}
             <div>
               <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">
                  <History className="w-4 h-4 text-gray-400" /> History
               </h4>
               <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
                   <table className="w-full text-sm text-left">
                       <thead className="bg-gray-50 text-gray-500">
                           <tr>
                               <th className="px-4 py-2 font-medium">Period</th>
                               <th className="px-4 py-2 font-medium">Status</th>
                               <th className="px-4 py-2 font-medium text-right">Variance</th>
                           </tr>
                       </thead>
                       <tbody className="divide-y divide-gray-50">
                           {ruleDetails.history.map((h, i) => (
                               <tr key={i} className="hover:bg-gray-50/50">
                                   <td className="px-4 py-2.5 text-gray-900">{h.date}</td>
                                   <td className="px-4 py-2.5">
                                       <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${
                                           h.status === 'pass' 
                                           ? 'bg-green-50 text-green-700' 
                                           : 'bg-amber-50 text-amber-700'
                                       }`}>
                                           {h.status === 'pass' ? 'Pass' : 'Warning'}
                                       </span>
                                   </td>
                                   <td className="px-4 py-2.5 text-right font-mono text-gray-600">
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
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
           <div className="flex items-center gap-3">
              <div className="flex -space-x-2">
                 <div className="w-6 h-6 rounded-full bg-blue-100 border-2 border-white flex items-center justify-center text-[10px] font-bold text-blue-700">JS</div>
                 <div className="w-6 h-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
                    <User className="w-3 h-3 text-gray-400" />
                 </div>
              </div>
              <span className="text-xs text-gray-500">Maintained by <strong>Finance Team</strong></span>
           </div>
           
           <div className="flex gap-3">
               <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-colors">
                   Edit Rule
               </button>
               <button 
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-200 transition-colors"
               >
                   Done
               </button>
           </div>
        </div>
      </div>
    </div>
  );
}
