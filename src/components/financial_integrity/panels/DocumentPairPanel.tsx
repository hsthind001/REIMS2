import React from 'react';
import { X, ExternalLink, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-react';
import type { ForensicMatch } from '../../../lib/forensic_reconciliation';

interface DocumentPairPanelProps {
  isOpen: boolean;
  onClose: () => void;
  pair: { source: string; target: string; value: number } | null;
  matches?: ForensicMatch[];
}

export default function DocumentPairPanel({ isOpen, onClose, pair, matches = [] }: DocumentPairPanelProps) {
  
  // Slide-over animation classes
  const panelClasses = `fixed inset-y-0 right-0 w-[480px] bg-white shadow-2xl transform transition-transform duration-300 ease-in-out z-40 ${
    isOpen ? 'translate-x-0' : 'translate-x-full'
  }`;

  if (!pair) return null;

  // Filter matches for this pair if explicit matches weren't passed (or assuming matches contains ALL matches)
  // Note: For now assuming 'matches' passed are relevant to the session or I need to filter them?
  // Actually, 'matches' passed from parent might be ALL matches in session. I should filter them.
  const relevantMatches = matches.length > 0 ? matches.filter(m => 
      (m.source_document_type === pair.source && m.target_document_type === pair.target) ||
      (m.source_document_type === pair.target && m.target_document_type === pair.source)
  ) : [];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div className={panelClasses}>
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-start bg-gray-50/50">
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                 <span className="font-medium bg-white px-2 py-0.5 rounded border border-gray-200">{pair.source}</span>
                 <ArrowRight className="w-3 h-3" />
                 <span className="font-medium bg-white px-2 py-0.5 rounded border border-gray-200">{pair.target}</span>
              </div>
              <h2 className="text-xl font-bold text-gray-900">Reconciliation Details</h2>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
             
             {/* Quick Stats */}
             <div className="grid grid-cols-2 gap-4">
                 <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                     <div className="text-green-600 font-bold text-2xl mb-1">
                         {Math.floor(pair.value * 0.85)} {/* Mock passed count base on total */}
                     </div>
                     <div className="text-xs font-medium text-green-800 uppercase tracking-wide flex items-center gap-1">
                         <CheckCircle2 className="w-3 h-3" /> Passed Checks
                     </div>
                 </div>
                 <div className="p-4 bg-amber-50 rounded-xl border border-amber-100">
                     <div className="text-amber-600 font-bold text-2xl mb-1">
                         {pair.value - Math.floor(pair.value * 0.85)}
                     </div>
                     <div className="text-xs font-medium text-amber-800 uppercase tracking-wide flex items-center gap-1">
                         <AlertTriangle className="w-3 h-3" /> Variances
                     </div>
                 </div>
             </div>

             {/* Active Rules */}
             <div>
                 <h3 className="font-bold text-gray-900 mb-3 flex items-center justify-between">
                     <span>Active Rules</span>
                     <span className="text-xs font-normal text-gray-500">3 Rules Applied</span>
                 </h3>
                 <div className="space-y-3">
                     {[1, 2, 3].map(i => (
                         <div key={i} className="flex items-start gap-3 p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors group">
                             <div className="mt-0.5">
                                 <div className="w-2 h-2 rounded-full bg-blue-500 ring-4 ring-blue-50" />
                             </div>
                             <div className="flex-1">
                                 <div className="flex justify-between">
                                     <h4 className="font-bold text-sm text-gray-900">Rule #{i}: Entity Name Check</h4>
                                     <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-bold">Pass</span>
                                 </div>
                                 <p className="text-xs text-gray-500 mt-1 line-clamp-1">Verifies that the entity name matches exactly between documents.</p>
                             </div>
                             <button className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-all">
                                 <ExternalLink className="w-4 h-4" />
                             </button>
                         </div>
                     ))}
                 </div>
             </div>

             {/* Recent Matches */}
             <div>
                <h3 className="font-bold text-gray-900 mb-3">Recent Matches</h3>
                {relevantMatches.length > 0 ? (
                    <div className="space-y-2">
                        {relevantMatches.map(match => (
                            <div key={match.id} className="p-3 border border-gray-100 rounded-lg text-sm">
                                <div className="flex justify-between font-medium">
                                    <span>Match #{match.id}</span>
                                    <span className={`${match.status === 'approved' ? 'text-green-600' : 'text-amber-600'}`}>
                                        {match.status}
                                    </span>
                                </div>
                                <div className="text-gray-500 text-xs mt-1">
                                    Conf: {match.confidence_score}% | {match.match_type}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-gray-400 text-xs italic bg-gray-50 rounded-lg border border-dashed border-gray-200">
                        No individual matches loaded for this pair yet.
                    </div>
                )}
             </div>

          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-100 bg-gray-50">
             <button className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2">
                 Run Deep Analysis
                 <ExternalLink className="w-4 h-4" />
             </button>
          </div>
        </div>
      </div>
    </>
  );
}
