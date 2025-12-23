/**
 * Discrepancy Panel Component
 * 
 * Displays discrepancies grouped by severity with resolution workflow
 */

import { useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { ForensicDiscrepancy } from '../../lib/forensic_reconciliation';

interface DiscrepancyPanelProps {
  discrepancies: ForensicDiscrepancy[];
  loading?: boolean;
  onResolve: (discrepancyId: number, resolutionNotes: string, newValue?: number) => void;
  severityFilter: string;
  onFilterChange: (severity: string) => void;
}

export default function DiscrepancyPanel({
  discrepancies,
  loading = false,
  onResolve,
  severityFilter,
  onFilterChange
}: DiscrepancyPanelProps) {
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState<{ [key: number]: string }>({});
  const [newValue, setNewValue] = useState<{ [key: number]: string }>({});

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-amber-100 text-amber-800 border-amber-300',
      low: 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return colors[severity] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  const getSeverityIcon = (severity: string) => {
    if (severity === 'critical' || severity === 'high') {
      return <AlertTriangle className="w-5 h-5" />;
    }
    return <AlertTriangle className="w-4 h-4" />;
  };

  const filteredDiscrepancies = discrepancies.filter(d => 
    severityFilter === 'all' || d.severity === severityFilter
  );

  const groupedBySeverity = {
    critical: filteredDiscrepancies.filter(d => d.severity === 'critical'),
    high: filteredDiscrepancies.filter(d => d.severity === 'high'),
    medium: filteredDiscrepancies.filter(d => d.severity === 'medium'),
    low: filteredDiscrepancies.filter(d => d.severity === 'low')
  };

  const handleResolve = (discrepancyId: number) => {
    const notes = resolutionNotes[discrepancyId] || '';
    const value = newValue[discrepancyId] ? parseFloat(newValue[discrepancyId]) : undefined;
    
    if (!notes.trim()) {
      alert('Please provide resolution notes');
      return;
    }
    
    onResolve(discrepancyId, notes, value);
    setResolvingId(null);
    setResolutionNotes(prev => ({ ...prev, [discrepancyId]: '' }));
    setNewValue(prev => ({ ...prev, [discrepancyId]: '' }));
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-gray-500">Loading discrepancies...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <Card className="p-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Severity Filter</label>
          <select
            value={severityFilter}
            onChange={(e) => onFilterChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </Card>

      {/* Discrepancies by Severity */}
      {Object.entries(groupedBySeverity).map(([severity, items]) => {
        if (items.length === 0) return null;
        
        return (
          <Card key={severity} className={`border-2 ${getSeverityColor(severity)}`}>
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {getSeverityIcon(severity)}
                  <h3 className="text-lg font-semibold capitalize">{severity}</h3>
                  <span className="px-2 py-1 text-xs font-semibold bg-white rounded-full">
                    {items.length}
                  </span>
                </div>
              </div>
              
              <div className="space-y-3">
                {items.map((discrepancy) => (
                  <div
                    key={discrepancy.id}
                    className="bg-white rounded-lg p-4 border border-gray-200"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-900">
                            {discrepancy.discrepancy_type}
                          </span>
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            discrepancy.status === 'resolved' ? 'bg-green-100 text-green-800' :
                            discrepancy.status === 'investigating' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {discrepancy.status}
                          </span>
                        </div>
                        
                        <p className="text-sm text-gray-700 mb-2">{discrepancy.description}</p>
                        
                        {discrepancy.difference !== undefined && (
                          <div className="flex gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">Difference:</span>
                              <span className="ml-2 font-semibold">
                                ${Math.abs(discrepancy.difference).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                              </span>
                            </div>
                            {discrepancy.difference_percent !== undefined && (
                              <div>
                                <span className="text-gray-600">Percent:</span>
                                <span className="ml-2 font-semibold">
                                  {discrepancy.difference_percent.toFixed(2)}%
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {discrepancy.suggested_resolution && (
                          <div className="mt-2 p-2 bg-blue-50 rounded text-sm text-blue-800">
                            <strong>Suggested:</strong> {discrepancy.suggested_resolution}
                          </div>
                        )}
                      </div>
                      
                      {discrepancy.status === 'open' && (
                        <div className="ml-4">
                          <button
                            onClick={() => setResolvingId(resolvingId === discrepancy.id ? null : discrepancy.id)}
                            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                          >
                            Resolve
                          </button>
                        </div>
                      )}
                    </div>
                    
                    {resolvingId === discrepancy.id && (
                      <div className="mt-4 p-4 bg-gray-50 rounded border">
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Resolution Notes *
                            </label>
                            <textarea
                              value={resolutionNotes[discrepancy.id] || ''}
                              onChange={(e) => setResolutionNotes(prev => ({ ...prev, [discrepancy.id]: e.target.value }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              rows={3}
                              placeholder="Explain how you resolved this discrepancy..."
                            />
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              New Value (Optional)
                            </label>
                            <input
                              type="number"
                              value={newValue[discrepancy.id] || ''}
                              onChange={(e) => setNewValue(prev => ({ ...prev, [discrepancy.id]: e.target.value }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Enter corrected value if applicable"
                            />
                          </div>
                          
                          <div className="flex gap-2">
                            <Button
                              onClick={() => handleResolve(discrepancy.id)}
                              variant="success"
                              size="sm"
                            >
                              Confirm Resolution
                            </Button>
                            <Button
                              onClick={() => {
                                setResolvingId(null);
                                setResolutionNotes(prev => ({ ...prev, [discrepancy.id]: '' }));
                                setNewValue(prev => ({ ...prev, [discrepancy.id]: '' }));
                              }}
                              variant="info"
                              size="sm"
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        );
      })}
      
      {filteredDiscrepancies.length === 0 && (
        <Card className="p-12 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <p className="text-gray-600">No discrepancies found</p>
        </Card>
      )}
    </div>
  );
}

