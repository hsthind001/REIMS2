/**
 * Reconciliation Work Queue Component
 * 
 * Displays exceptions grouped by severity (Critical → High → Medium → Info)
 * with tier information, materiality, detector agreement, and age.
 */
import { useState } from 'react';
import { 
  AlertTriangle, 
  Clock, 
  User, 
  TrendingUp,
  CheckCircle,
  XCircle,
  MoreVertical
} from 'lucide-react';
import { Card, Button } from '../design-system';
import type { ForensicMatch, ForensicDiscrepancy } from '../../lib/forensic_reconciliation';

interface ReconciliationWorkQueueProps {
  matches: ForensicMatch[];
  discrepancies: ForensicDiscrepancy[];
  onApprove: (matchId: number) => void;
  onReject: (matchId: number, reason: string) => void;
  onViewDetails: (item: ForensicMatch | ForensicDiscrepancy) => void;
  onRouteToCommittee?: (matchId: number, committeeId: number) => void;
  filters?: {
    severity?: string;
    tier?: string;
    assignedTo?: number;
    needsMe?: boolean;
  };
}

interface ExceptionRow {
  id: number;
  type: 'match' | 'discrepancy';
  severity: 'critical' | 'high' | 'medium' | 'low';
  tier?: string;
  issueType: string;
  amountImpact: number;
  confidence: number;
  materiality: string;
  detectorAgreement?: number;
  age: number; // days
  assignedTo?: number;
  assignedToName?: string;
  match?: ForensicMatch;
  discrepancy?: ForensicDiscrepancy;
}

export default function ReconciliationWorkQueue({
  matches,
  discrepancies,
  onApprove,
  onReject,
  onViewDetails,
  onRouteToCommittee,
  filters
}: ReconciliationWorkQueueProps) {
  const [selectedExceptions, setSelectedExceptions] = useState<Set<number>>(new Set());

  // Convert matches and discrepancies to exception rows
  const exceptionRows: ExceptionRow[] = [
    ...matches.map(match => ({
      id: match.id,
      type: 'match' as const,
      severity: match.confidence_score >= 70 ? 'medium' : 'high' as 'critical' | 'high' | 'medium' | 'low',
      tier: match.exception_tier || 'tier_2_route',
      issueType: `${match.source_document_type} → ${match.target_document_type}`,
      amountImpact: match.amount_difference ? Math.abs(parseFloat(match.amount_difference.toString())) : 0,
      confidence: parseFloat(match.confidence_score.toString()),
      materiality: match.amount_difference && Math.abs(parseFloat(match.amount_difference.toString())) > 1000 ? 'Material' : 'Immaterial',
      age: match.created_at ? Math.floor((Date.now() - new Date(match.created_at).getTime()) / (1000 * 60 * 60 * 24)) : 0,
      match
    })),
    ...discrepancies.map(disc => ({
      id: disc.id,
      type: 'discrepancy' as const,
      severity: disc.severity as 'critical' | 'high' | 'medium' | 'low',
      tier: disc.exception_tier || 'tier_2_route',
      issueType: disc.discrepancy_type,
      amountImpact: disc.difference ? Math.abs(parseFloat(disc.difference.toString())) : 0,
      confidence: 50, // Discrepancies don't have confidence, use default
      materiality: disc.difference && Math.abs(parseFloat(disc.difference.toString())) > 1000 ? 'Material' : 'Immaterial',
      age: disc.created_at ? Math.floor((Date.now() - new Date(disc.created_at).getTime()) / (1000 * 60 * 60 * 24)) : 0,
      discrepancy: disc
    }))
  ];

  // Group by severity
  const grouped = {
    critical: exceptionRows.filter(e => e.severity === 'critical'),
    high: exceptionRows.filter(e => e.severity === 'high'),
    medium: exceptionRows.filter(e => e.severity === 'medium'),
    low: exceptionRows.filter(e => e.severity === 'low')
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-50';
      case 'high': return 'border-orange-500 bg-orange-50';
      case 'medium': return 'border-yellow-500 bg-yellow-50';
      case 'low': return 'border-blue-500 bg-blue-50';
      default: return 'border-gray-300 bg-gray-50';
    }
  };

  const getTierLabel = (tier?: string) => {
    if (!tier) return 'Not Classified';
    switch (tier) {
      case 'tier_0_auto_close': return 'Tier 0: Auto-Close';
      case 'tier_1_auto_suggest': return 'Tier 1: Auto-Suggest';
      case 'tier_2_route': return 'Tier 2: Route';
      case 'tier_3_escalate': return 'Tier 3: Escalate';
      default: return tier;
    }
  };

  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedExceptions);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedExceptions(newSelection);
  };

  const renderExceptionRow = (exception: ExceptionRow) => {
    const isSelected = selectedExceptions.has(exception.id);
    
    return (
      <tr 
        key={exception.id}
        className={`border-b hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}
      >
        <td className="px-4 py-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleSelection(exception.id)}
            className="rounded border-gray-300"
          />
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{exception.issueType}</span>
            {exception.tier && (
              <span className="text-xs px-2 py-1 rounded bg-gray-200 text-gray-700">
                {getTierLabel(exception.tier)}
              </span>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <span className="text-sm font-semibold">
            ${exception.amountImpact.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-16 bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${
                  exception.confidence >= 90 ? 'bg-green-500' :
                  exception.confidence >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${exception.confidence}%` }}
              />
            </div>
            <span className="text-sm text-gray-600">{exception.confidence.toFixed(0)}%</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <span className={`text-xs px-2 py-1 rounded ${
            exception.materiality === 'Material' 
              ? 'bg-red-100 text-red-700' 
              : 'bg-gray-100 text-gray-700'
          }`}>
            {exception.materiality}
          </span>
        </td>
        <td className="px-4 py-3">
          {exception.detectorAgreement !== undefined ? (
            <span className="text-sm text-gray-600">{exception.detectorAgreement}%</span>
          ) : (
            <span className="text-sm text-gray-400">N/A</span>
          )}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1 text-sm text-gray-600">
            <Clock className="w-4 h-4" />
            <span>{exception.age}d</span>
          </div>
        </td>
        <td className="px-4 py-3">
          {exception.assignedToName ? (
            <div className="flex items-center gap-1 text-sm">
              <User className="w-4 h-4 text-gray-400" />
              <span>{exception.assignedToName}</span>
            </div>
          ) : (
            <span className="text-sm text-gray-400">Unassigned</span>
          )}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {exception.match ? (
              <>
                <Button
                  variant="success"
                  size="sm"
                  onClick={() => onApprove(exception.match!.id)}
                  icon={<CheckCircle className="w-4 h-4" />}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => onReject(exception.match!.id, 'Rejected from work queue')}
                  icon={<XCircle className="w-4 h-4" />}
                >
                  Reject
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onViewDetails(exception.match!)}
                >
                  View
                </Button>
              </>
            ) : exception.discrepancy ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onViewDetails(exception.discrepancy!)}
              >
                View Details
              </Button>
            ) : null}
          </div>
        </td>
      </tr>
    );
  };

  return (
    <div className="space-y-6">
      {/* Bulk Actions Bar */}
      {selectedExceptions.size > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-blue-900">
              {selectedExceptions.size} exception(s) selected
            </span>
            <div className="flex gap-2">
              <Button
                variant="success"
                size="sm"
                onClick={() => {
                  selectedExceptions.forEach(id => {
                    const exception = exceptionRows.find(e => e.id === id);
                    if (exception?.match) {
                      onApprove(id);
                    }
                  });
                  setSelectedExceptions(new Set());
                }}
              >
                Bulk Approve
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => {
                  selectedExceptions.forEach(id => {
                    const exception = exceptionRows.find(e => e.id === id);
                    if (exception?.match) {
                      onReject(id, 'Bulk rejected');
                    }
                  });
                  setSelectedExceptions(new Set());
                }}
              >
                Bulk Reject
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Critical Exceptions */}
      {grouped.critical.length > 0 && (
        <Card className={`border-2 ${getSeverityColor('critical')}`}>
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <h3 className="text-lg font-semibold text-red-900">Critical ({grouped.critical.length})</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-red-100">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Select</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Issue Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Amount Impact</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Confidence</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Materiality</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Agreement</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Age</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Assigned To</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-red-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {grouped.critical.map(renderExceptionRow)}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* High Exceptions */}
      {grouped.high.length > 0 && (
        <Card className={`border-2 ${getSeverityColor('high')}`}>
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              <h3 className="text-lg font-semibold text-orange-900">High ({grouped.high.length})</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-orange-100">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Select</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Issue Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Amount Impact</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Confidence</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Materiality</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Agreement</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Age</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Assigned To</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-orange-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {grouped.high.map(renderExceptionRow)}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Medium Exceptions */}
      {grouped.medium.length > 0 && (
        <Card className={`border-2 ${getSeverityColor('medium')}`}>
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              <h3 className="text-lg font-semibold text-yellow-900">Medium ({grouped.medium.length})</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-yellow-100">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Select</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Issue Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Amount Impact</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Confidence</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Materiality</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Agreement</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Age</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Assigned To</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-yellow-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {grouped.medium.map(renderExceptionRow)}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Low/Info Exceptions */}
      {grouped.low.length > 0 && (
        <Card className={`border-2 ${getSeverityColor('low')}`}>
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold text-blue-900">Info ({grouped.low.length})</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-blue-100">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Select</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Issue Type</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Amount Impact</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Confidence</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Materiality</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Agreement</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Age</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Assigned To</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-blue-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {grouped.low.map(renderExceptionRow)}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Empty State */}
      {exceptionRows.length === 0 && (
        <Card className="p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-900 mb-2">No exceptions found</p>
          <p className="text-sm text-gray-600">
            All matches have been reviewed or no reconciliation has been run yet.
          </p>
        </Card>
      )}
    </div>
  );
}

