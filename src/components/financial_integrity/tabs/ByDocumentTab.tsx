import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  CheckCircle2, 
  AlertTriangle,
  Calculator,
  MinusCircle,
  FileText
} from 'lucide-react';
import type { CalculatedRuleEvaluation } from '../../../lib/forensic_reconciliation';

interface ByDocumentTabProps {
  documents?: any[]; // Replace with proper type
  rules?: CalculatedRuleEvaluation[];
}

export default function ByDocumentTab({ documents = [], rules = [] }: ByDocumentTabProps) {
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  // Helper to filter rules for a specific document
  const getRulesForDoc = (docId: string) => {
      if (!rules.length) return [];
      
      const docPrefixMap: Record<string, string> = {
          'balance_sheet': 'BS',
          'income_statement': 'IS',
          'cash_flow': 'CF',
          'rent_roll': 'RR',
          'mortgage_statement': 'MS'
      };

      const prefix = docPrefixMap[docId];

      return rules.filter(r => {
          if (prefix && r.rule_id.startsWith(prefix)) return true;
          
          // Fallback heuristics
          return r.formula.includes(`${docId}.`) || 
                 r.rule_name.toLowerCase().includes(docId.replace('_', ' ')) ||
                 (r.description && r.description.toLowerCase().includes(docId.replace('_', ' ')));
      });
  };

  const currentRules = expandedDoc ? getRulesForDoc(expandedDoc) : [];

  return (
    <div className="space-y-4">
        {documents.map(doc => {
            const docRules = getRulesForDoc(doc.id);
            const activeRuleCount = docRules.length;

            return (
            <div key={doc.id} className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm transition-all hover:shadow-md">
                
                {/* Header / Summary Row */}
                <div 
                    className={`p-4 flex items-center justify-between cursor-pointer ${expandedDoc === doc.id ? 'bg-gray-50' : 'bg-white'}`}
                    onClick={() => setExpandedDoc(expandedDoc === doc.id ? null : doc.id)}
                >
                    <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${doc.failed === 0 ? 'bg-green-100 text-green-600' : 'bg-amber-100 text-amber-600'}`}>
                            {doc.type === 'Financial' ? <Calculator className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-900">{doc.name}</h3>
                            <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                                <span>{activeRuleCount || doc.rules} Active Rules</span>
                                <span className="w-1 h-1 rounded-full bg-gray-300" />
                                <span>Last sync: {doc.lastSync || 'Just now'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        {/* Mini Status Bar */}
                        <div className="flex gap-1">
                             <div className="flex flex-col items-center">
                                 <span className="text-xs font-bold text-green-600">{doc.passed}</span>
                                 <span className="text-[10px] text-gray-400 uppercase">Pass</span>
                             </div>
                             <div className="w-px h-8 bg-gray-100 mx-2" />
                             <div className="flex flex-col items-center">
                                 <span className={`text-xs font-bold ${doc.failed > 0 ? 'text-amber-600' : 'text-gray-300'}`}>{doc.failed}</span>
                                 <span className="text-[10px] text-gray-400 uppercase">Fail</span>
                             </div>
                        </div>

                        {expandedDoc === doc.id ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
                    </div>
                </div>

                {/* Expanded Details */}
                {expandedDoc === doc.id && (
                    <div className="border-t border-gray-100 bg-white p-4">
                        {currentRules.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {currentRules.map(rule => (
                                    <div key={rule.rule_id} className="border border-gray-100 rounded-lg p-3 hover:border-blue-200 transition-colors group">
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2 overflow-hidden">
                                                {rule.status === 'PASS' ? <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" /> : 
                                                 rule.status === 'FAIL' ? <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" /> :
                                                 <MinusCircle className="w-4 h-4 text-gray-400 shrink-0" />}
                                                <span className="font-medium text-gray-700 text-sm truncate group-hover:text-blue-700" title={rule.rule_name}>
                                                    {rule.rule_name}
                                                </span>
                                            </div>
                                            <span className={`text-xs font-mono font-medium whitespace-nowrap ml-2 ${
                                                rule.status === 'PASS' ? 'text-gray-600' : 'text-red-600'
                                            }`}>
                                                {rule.actual_value !== undefined && rule.actual_value !== null 
                                                    ? `$${rule.actual_value.toLocaleString()}` 
                                                    : 'N/A'}
                                            </span>
                                        </div>
                                        
                                        <div className="bg-gray-50 rounded px-2 py-1 text-xs font-mono text-gray-500 mb-2 truncate" title={rule.formula}>
                                            {rule.formula}
                                        </div>

                                        <div className="flex justify-between items-center mt-2">
                                            {rule.status === 'FAIL' && (
                                                <div className="text-xs text-amber-600 font-medium bg-amber-50 px-2 py-0.5 rounded">
                                                    Diff: {rule.difference ? `$${rule.difference.toLocaleString()}` : 'Unknown'}
                                                </div>
                                            )}
                                            <span className="text-[10px] text-gray-400 uppercase tracking-wider ml-auto">
                                                {rule.severity || 'LOW'}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-6 text-gray-400 text-sm italic">
                                No specific rules found linked to this document type in the current rule set.
                            </div>
                        )}
                    </div>
                )}
            </div>
        )})}
    </div>
  );
}
