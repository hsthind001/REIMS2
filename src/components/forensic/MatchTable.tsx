/**
 * Match Table Component
 * 
 * Sortable table of all matches with color-coded confidence scores
 * and inline approve/reject functionality
 */

import { useState, useMemo } from 'react';
import { CheckCircle, XCircle, Eye, ArrowUpDown } from 'lucide-react';
import { Card } from '../design-system';
import type { ForensicMatch } from '../../lib/forensic_reconciliation';

interface MatchTableProps {
  matches: ForensicMatch[];
  loading?: boolean;
  onApprove: (matchId: number) => void;
  onReject: (matchId: number, reason: string) => void;
  onViewDetails: (match: ForensicMatch) => void;
  matchTypeFilter: string;
  statusFilter: string;
  onFilterChange: (matchType: string, status: string) => void;
}

export default function MatchTable({
  matches,
  loading = false,
  onApprove,
  onReject,
  onViewDetails,
  matchTypeFilter,
  statusFilter,
  onFilterChange
}: MatchTableProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({
    key: 'confidence_score',
    direction: 'desc'
  });
  const [rejectReason, setRejectReason] = useState<{ [key: number]: string }>({});
  const [showRejectInput, setShowRejectInput] = useState<number | null>(null);

  const sortedMatches = useMemo(() => {
    const sorted = [...matches];
    sorted.sort((a, b) => {
      const aValue = a[sortConfig.key as keyof ForensicMatch];
      const bValue = b[sortConfig.key as keyof ForensicMatch];
      
      if (aValue === undefined || aValue === null) return 1;
      if (bValue === undefined || bValue === null) return -1;
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return 0;
    });
    return sorted;
  }, [matches, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-50';
    if (score >= 70) return 'text-blue-600 bg-blue-50';
    if (score >= 50) return 'text-amber-600 bg-amber-50';
    return 'text-red-600 bg-red-50';
  };

  const getMatchTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      exact: 'bg-green-100 text-green-800',
      fuzzy: 'bg-blue-100 text-blue-800',
      calculated: 'bg-purple-100 text-purple-800',
      inferred: 'bg-amber-100 text-amber-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const handleReject = (matchId: number) => {
    const reason = rejectReason[matchId] || 'No reason provided';
    onReject(matchId, reason);
    setShowRejectInput(null);
    setRejectReason(prev => ({ ...prev, [matchId]: '' }));
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-gray-500">Loading matches...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Match Type</label>
            <select
              value={matchTypeFilter}
              onChange={(e) => onFilterChange(e.target.value, statusFilter)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              <option value="exact">Exact</option>
              <option value="fuzzy">Fuzzy</option>
              <option value="calculated">Calculated</option>
              <option value="inferred">Inferred</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => onFilterChange(matchTypeFilter, e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="modified">Modified</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Match Count Info */}
      {matches.length > 0 && (
        <div className="text-sm text-gray-600 mb-2">
          Showing {sortedMatches.length} of {matches.length} matches
        </div>
      )}

      {/* Table */}
      <Card className="overflow-hidden">
        {sortedMatches.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg font-medium mb-2">No matches found</p>
            <p className="text-sm">
              {matchTypeFilter !== 'all' || statusFilter !== 'all'
                ? 'Try adjusting your filters to see more matches.'
                : 'No matches were found for this session. Run reconciliation to find matches.'}
            </p>
          </div>
        ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('id')}
                >
                  <div className="flex items-center gap-2">
                    ID
                    <ArrowUpDown className="w-4 h-4" />
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source → Target
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Match Type
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('confidence_score')}
                >
                  <div className="flex items-center gap-2">
                    Confidence
                    <ArrowUpDown className="w-4 h-4" />
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Difference
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedMatches.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    No matches found
                  </td>
                </tr>
              ) : (
                sortedMatches.map((match) => (
                  <tr key={match.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {match.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{match.source_document_type}</span>
                        <span className="text-gray-400">→</span>
                        <span className="font-medium">{match.target_document_type}</span>
                      </div>
                      {match.relationship_formula && (
                        <div className="text-xs text-gray-500 mt-1">{match.relationship_formula}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getMatchTypeColor(match.match_type)}`}>
                        {match.match_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getConfidenceColor(match.confidence_score)}`}>
                        {match.confidence_score.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {match.amount_difference !== undefined && (
                        <div>
                          <div className="font-medium">
                            ${Math.abs(match.amount_difference).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </div>
                          {match.amount_difference_percent !== undefined && (
                            <div className="text-xs text-gray-500">
                              {match.amount_difference_percent.toFixed(2)}%
                            </div>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        match.status === 'approved' ? 'bg-green-100 text-green-800' :
                        match.status === 'rejected' ? 'bg-red-100 text-red-800' :
                        match.status === 'modified' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {match.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onViewDetails(match)}
                          className="text-blue-600 hover:text-blue-800"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {match.status === 'pending' && (
                          <>
                            <button
                              onClick={() => onApprove(match.id)}
                              className="text-green-600 hover:text-green-800"
                              title="Approve"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setShowRejectInput(showRejectInput === match.id ? null : match.id)}
                              className="text-red-600 hover:text-red-800"
                              title="Reject"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                      {showRejectInput === match.id && (
                        <div className="mt-2 p-2 bg-gray-50 rounded border">
                          <input
                            type="text"
                            placeholder="Rejection reason..."
                            value={rejectReason[match.id] || ''}
                            onChange={(e) => setRejectReason(prev => ({ ...prev, [match.id]: e.target.value }))}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded mb-2"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                handleReject(match.id);
                              }
                            }}
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleReject(match.id)}
                              className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                            >
                              Confirm Reject
                            </button>
                            <button
                              onClick={() => {
                                setShowRejectInput(null);
                                setRejectReason(prev => ({ ...prev, [match.id]: '' }));
                              }}
                              className="px-3 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

