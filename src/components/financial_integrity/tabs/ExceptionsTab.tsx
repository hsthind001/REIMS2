import React from 'react';
import { 
  AlertTriangle, 
  Clock, 
  ArrowRight,
  Filter,
  FileText
} from 'lucide-react';

interface ExceptionsTabProps {
  discrepancies: any[]; // Replace with ForensicDiscrepancy[] when available
}

export default function ExceptionsTab({ discrepancies }: ExceptionsTabProps) {
  return (
    <div className="space-y-6">
        {/* Header Stats */}
        <div className="grid grid-cols-4 gap-4">
            <div className="bg-red-50 border border-red-100 p-4 rounded-xl">
                <div className="text-red-600 font-medium text-sm mb-1">Critical Issues</div>
                <div className="text-2xl font-bold text-red-700">{discrepancies.filter(d => d.severity === 'high').length}</div>
            </div>
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl">
                <div className="text-amber-600 font-medium text-sm mb-1">Warnings</div>
                <div className="text-2xl font-bold text-amber-700">{discrepancies.filter(d => d.severity === 'medium').length}</div>
            </div>
            <div className="bg-blue-50 border border-blue-100 p-4 rounded-xl">
                <div className="text-blue-600 font-medium text-sm mb-1">In Progress</div>
                <div className="text-2xl font-bold text-blue-700">{discrepancies.filter(d => d.status === 'in_progress').length}</div>
            </div>
            <div className="bg-green-50 border border-green-100 p-4 rounded-xl">
                <div className="text-green-600 font-medium text-sm mb-1">Resolved Today</div>
                <div className="text-2xl font-bold text-green-700">0</div>
            </div>
        </div>

        {/* List Header */}
        <div className="flex justify-between items-center">
            <h3 className="font-bold text-gray-900">Active Exceptions</h3>
            <div className="flex gap-2">
                <button className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 flex items-center gap-2 hover:bg-gray-50">
                    <Filter className="w-4 h-4" /> Filter
                </button>
            </div>
        </div>

        {/* Exceptions List */}
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm divide-y divide-gray-50">
            {discrepancies.length > 0 ? discrepancies.map(item => (
                <div key={item.id} className="p-5 hover:bg-gray-50 transition-colors group">
                    <div className="flex justify-between items-start">
                        <div className="flex gap-4">
                            <div className={`mt-1 p-2 rounded-lg ${
                                item.severity === 'high' ? 'bg-red-100 text-red-600' :
                                item.severity === 'medium' ? 'bg-amber-100 text-amber-600' :
                                'bg-blue-100 text-blue-600'
                            }`}>
                                <AlertTriangle className="w-5 h-5" />
                            </div>
                            
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <h4 className="font-bold text-gray-900">{item.description || 'Discrepancy Detected'}</h4>
                                    <span className="text-xs font-mono text-gray-400 border border-gray-100 px-1.5 rounded">{item.id}</span>
                                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                        item.status === 'open' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                                    }`}>
                                        {item.status ? item.status.replace('_', ' ') : 'OPEN'}
                                    </span>
                                </div>
                                <p className="text-sm text-gray-600">{item.notes || 'No details available.'}</p>
                                
                                <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                                    <div className="flex items-center gap-1">
                                        <FileText className="w-3 h-3" /> {item.source_item || 'Unknown Source'}
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Clock className="w-3 h-3" /> {item.created_at || 'Recently'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="text-right">
                            <div className="font-bold text-gray-900">{item.amount_difference ? `$${item.amount_difference}` : '-'}</div>
                            <div className="text-xs text-gray-500 uppercase font-medium mt-0.5">Impact</div>
                            
                            <button className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-800 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-end gap-1 w-full">
                                Resolve <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            )) : (
                 <div className="p-8 text-center text-gray-500">No active exceptions found.</div>
            )}
        </div>
    </div>
  );
}
