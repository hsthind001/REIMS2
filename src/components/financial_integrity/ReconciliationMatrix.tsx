import React, { useMemo } from 'react';
import type { ForensicMatch } from '../../lib/forensic_reconciliation';

interface ReconciliationMatrixProps {
  matches: ForensicMatch[];
  onCellClick: (source: string, target: string, value: number) => void;
}

const DOCUMENTS = [
  { id: 'balance_sheet', label: 'Balance Sheet', short: 'BS' },
  { id: 'income_statement', label: 'Income Statement', short: 'IS' },
  { id: 'cash_flow', label: 'Cash Flow', short: 'CF' },
  { id: 'rent_roll', label: 'Rent Roll', short: 'RR' },
  { id: 'mortgage_statement', label: 'Mortgage Stmt', short: 'MS' }
];

export default function ReconciliationMatrix({ matches, onCellClick }: ReconciliationMatrixProps) {
  
  // Calculate grid data
  const gridData = useMemo(() => {
    const data: Record<string, Record<string, { total: number, passed: number, variance: number, warning: number }>> = {};
    
    // Initialize
    DOCUMENTS.forEach(d1 => {
        data[d1.id] = {};
        DOCUMENTS.forEach(d2 => {
            data[d1.id][d2.id] = { total: 0, passed: 0, variance: 0, warning: 0 };
        });
    });

    // Document type normalization map (backend might use different formats)
    const normalizeDocType = (docType: string): string => {
      const normalized = docType.toLowerCase().replace(/\s+/g, '_');
      
      // Map common variations
      const mappings: Record<string, string> = {
        'balancesheet': 'balance_sheet',
        'balance_sheet': 'balance_sheet',
        'incomestatement': 'income_statement',
        'income_statement': 'income_statement',
        'cashflow': 'cash_flow',
        'cash_flow': 'cash_flow',
        'rentroll': 'rent_roll',
        'rent_roll': 'rent_roll',
        'mortgagestatement': 'mortgage_statement',
        'mortgage_statement': 'mortgage_statement',
        'mortgage_stmt': 'mortgage_statement',
      };
      
      return mappings[normalized] || normalized;
    };

    // Aggregate matches
    matches.forEach(m => {
        const source = normalizeDocType(m.source_document_type);
        const target = normalizeDocType(m.target_document_type);
        
        if (data[source] && data[source][target]) {
            data[source][target].total++;
            
            // Perfect match: approved status OR confidence score is 100%
            if (m.status === 'approved' || m.confidence_score >= 1.0) {
                data[source][target].passed++;
            } 
            // Warning: pending with low confidence
            else if (m.status === 'pending' && m.confidence_score < 0.8) {
                data[source][target].warning++;
            } 
            // Variance: anything else (rejected, modified, or mid-confidence pending)
            else {
                data[source][target].variance++;
            }
        } else {
          // Log unmatched document types for debugging
          if (process.env.NODE_ENV === 'development') {
            console.warn(`Unmatched document types in ReconciliationMatrix: ${source} -> ${target}`);
          }
        }
    });

    // Log summary for debugging
    if (process.env.NODE_ENV === 'development' && matches.length > 0) {
      console.log('ReconciliationMatrix Data Summary:', {
        totalMatches: matches.length,
        gridData: data,
        documentTypes: matches.map(m => ({
          source: m.source_document_type,
          target: m.target_document_type,
          normalized_source: normalizeDocType(m.source_document_type),
          normalized_target: normalizeDocType(m.target_document_type),
        }))
      });
    }

    return data;
  }, [matches]);

  const getCellStatus = (source: string, target: string) => {
      if (source === target) return 'self';
      
      const stat = gridData[source]?.[target];
      if (!stat || stat.total === 0) return 'na';
      
      if (stat.warning > 0 || stat.variance > 0) return 'variance';
      return 'perfect'; // All passed
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-gray-50/30">
        <div>
           <h3 className="text-lg font-bold text-gray-900">Reconciliation Matrix</h3>
           <p className="text-sm text-gray-500 mt-1">Cross-document validation status map</p>
        </div>
        
        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-medium text-gray-600">
            <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div> Perfect Match
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500"></div> Variance
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-gray-200"></div> No Rules
            </div>
        </div>
      </div>
      
      <div className="p-6 overflow-x-auto">
        <table className="w-full border-collapse min-w-[600px]">
             <thead>
                 <tr>
                    <th className="w-32"></th>
                    {DOCUMENTS.map(doc => (
                        <th key={doc.id} className="pb-4 text-center font-semibold text-xs text-gray-500 uppercase tracking-wider">
                            {doc.short}
                        </th>
                    ))}
                 </tr>
             </thead>
             <tbody>
                 {DOCUMENTS.map(sourceDoc => (
                     <tr key={sourceDoc.id}>
                         {/* Row Label */}
                         <td className="text-right pr-6 py-2 text-sm font-medium text-gray-700 whitespace-nowrap">
                             {sourceDoc.label}
                         </td>
                         
                         {/* Cells */}
                         {DOCUMENTS.map(targetDoc => {
                             const status = getCellStatus(sourceDoc.id, targetDoc.id);
                             const stats = gridData[sourceDoc.id]?.[targetDoc.id];
                             
                             return (
                                <td key={`${sourceDoc.id}-${targetDoc.id}`} className="p-1">
                                    <div 
                                        onClick={() => status !== 'self' && status !== 'na' && onCellClick(sourceDoc.id, targetDoc.id, stats?.total || 0)}
                                        className={`
                                            h-14 rounded-lg border flex flex-col items-center justify-center transition-all duration-200 relative group
                                            ${status === 'self' 
                                                ? 'bg-gray-50 border-gray-100 cursor-default opacity-50' 
                                                : status === 'na'
                                                    ? 'bg-white border-dashed border-gray-200 text-gray-300 cursor-default'
                                                    : 'cursor-pointer hover:shadow-md hover:scale-[1.02] hover:z-10'
                                            }
                                            ${status === 'perfect' ? 'bg-emerald-50/50 border-emerald-100 hover:border-emerald-300' : ''}
                                            ${status === 'variance' ? 'bg-amber-50/50 border-amber-100 hover:border-amber-300' : ''}
                                        `}
                                    >
                                        {status === 'self' ? (
                                            <div className="w-1.5 h-1.5 rounded-full bg-gray-300"></div>
                                        ) : status === 'na' ? (
                                            <span className="text-xs font-medium">-</span>
                                        ) : (
                                            <>
                                                <div className={`font-bold text-lg ${
                                                    status === 'perfect' ? 'text-emerald-600' : 'text-amber-600'
                                                }`}>
                                                    {stats?.total || 0}
                                                </div>
                                                {status === 'variance' && (
                                                    <div className="absolute top-1.5 right-1.5">
                                                        <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
                                                    </div>
                                                )}
                                                <span className={`text-[10px] uppercase font-bold tracking-wide ${
                                                     status === 'perfect' ? 'text-emerald-700' : 'text-amber-700'
                                                }`}>
                                                    {status === 'perfect' ? 'MATCH' : 'VARIANCE'}
                                                </span>
                                            </>
                                        )}
                                    </div>
                                </td>
                             );
                         })}
                     </tr>
                 ))}
             </tbody>
        </table>
      </div>
    </div>
  );
}
