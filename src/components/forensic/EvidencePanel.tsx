/**
 * Evidence Panel Component
 * 
 * Right panel showing side-by-side values, computed formula, PDF links, and actions
 */
import { FileText, ExternalLink, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { ForensicMatch } from '../../lib/forensic_reconciliation';
import WhyFlaggedCard from './WhyFlaggedCard';
import ResolutionSuggestions from './ResolutionSuggestions';
import PeriodComparison from './PeriodComparison';

interface EvidencePanelProps {
  match: ForensicMatch | null;
  onApprove: (matchId: number) => void;
  onReject: (matchId: number, reason: string) => void;
  onRemap?: (matchId: number, newMapping: any) => void;
  onAddNote?: (matchId: number, note: string) => void;
  onCreateTask?: (matchId: number, task: any) => void;
}

export default function EvidencePanel({
  match,
  onApprove,
  onReject,
  onRemap,
  onAddNote,
  onCreateTask
}: EvidencePanelProps) {
  if (!match) {
    return (
      <Card className="p-6">
        <div className="text-center text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-sm">Select a match to view evidence</p>
        </div>
      </Card>
    );
  }

  const sourceAmount = match.source_amount ? parseFloat(match.source_amount.toString()) : 0;
  const targetAmount = match.target_amount ? parseFloat(match.target_amount.toString()) : 0;
  const difference = match.amount_difference ? parseFloat(match.amount_difference.toString()) : 0;
  const confidence = parseFloat(match.confidence_score.toString());

  return (
    <Card className="p-6 space-y-6">
      {/* Match Header */}
      <div className="border-b pb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">Match Evidence</h3>
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            confidence >= 90 ? 'bg-green-100 text-green-700' :
            confidence >= 70 ? 'bg-yellow-100 text-yellow-700' :
            'bg-red-100 text-red-700'
          }`}>
            {confidence.toFixed(0)}% Confidence
          </span>
        </div>
        <p className="text-sm text-gray-600">
          {match.source_document_type} → {match.target_document_type}
        </p>
      </div>

      {/* Side-by-Side Values */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border rounded-lg p-4">
          <div className="text-xs font-medium text-gray-500 mb-1">Source</div>
          <div className="text-lg font-semibold text-gray-900 mb-2">
            {match.source_account_code} - {match.source_account_name}
          </div>
          <div className="text-2xl font-bold text-gray-900">
            ${sourceAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {match.source_document_type.replace('_', ' ')}
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <div className="text-xs font-medium text-gray-500 mb-1">Target</div>
          <div className="text-lg font-semibold text-gray-900 mb-2">
            {match.target_account_code} - {match.target_account_name}
          </div>
          <div className="text-2xl font-bold text-gray-900">
            ${targetAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {match.target_document_type.replace('_', ' ')}
          </div>
        </div>
      </div>

      {/* Difference */}
      {difference !== 0 && (
        <div className={`p-3 rounded-lg ${
          Math.abs(difference) < 1 ? 'bg-yellow-50 border border-yellow-200' :
          Math.abs(difference) < 100 ? 'bg-orange-50 border border-orange-200' :
          'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Difference</span>
            <span className={`text-lg font-bold ${
              Math.abs(difference) < 1 ? 'text-yellow-700' :
              Math.abs(difference) < 100 ? 'text-orange-700' :
              'text-red-700'
            }`}>
              ${Math.abs(difference).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          {match.amount_difference_percent && (
            <div className="text-xs text-gray-600 mt-1">
              {Math.abs(parseFloat(match.amount_difference_percent.toString())).toFixed(2)}% difference
            </div>
          )}
        </div>
      )}

      {/* Formula (for calculated matches) */}
      {match.relationship_formula && (
        <div className="border rounded-lg p-4 bg-gray-50">
          <div className="text-xs font-medium text-gray-500 mb-2">Relationship Formula</div>
          <code className="text-sm text-gray-900 font-mono">
            {match.relationship_formula}
          </code>
          {match.relationship_type && (
            <div className="mt-2 text-xs text-gray-600">
              Type: {match.relationship_type}
            </div>
          )}
        </div>
      )}

      {/* PDF Links */}
      <div className="space-y-2">
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          icon={<ExternalLink className="w-4 h-4" />}
          onClick={() => {
            // TODO: Open PDF viewer with highlighted value
            console.log('Open PDF for source document');
          }}
        >
          View Source PDF
        </Button>
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          icon={<ExternalLink className="w-4 h-4" />}
          onClick={() => {
            // TODO: Open PDF viewer with highlighted value
            console.log('Open PDF for target document');
          }}
        >
          View Target PDF
        </Button>
      </div>

      {/* Actions */}
      <div className="border-t pt-4 space-y-2">
        <Button
          variant="success"
          className="w-full"
          icon={<CheckCircle className="w-4 h-4" />}
          onClick={() => onApprove(match.id)}
        >
          Approve Match
        </Button>
        <Button
          variant="danger"
          className="w-full"
          icon={<XCircle className="w-4 h-4" />}
          onClick={() => onReject(match.id, 'Rejected from evidence panel')}
        >
          Reject Match
        </Button>
        {onRemap && (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              // TODO: Open remap dialog
              console.log('Remap account');
            }}
          >
            Remap Account
          </Button>
        )}
        {onAddNote && (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              // TODO: Open note dialog
              console.log('Add note');
            }}
          >
            Add Note
          </Button>
        )}
        {onCreateTask && (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              // TODO: Open task creation dialog
              console.log('Create task');
            }}
          >
            Create Task
          </Button>
        )}
      </div>

      {/* Explainability Section */}
      <div className="border-t pt-4 space-y-4">
        <WhyFlaggedCard
          reasons={[]}
          matchType={match.match_type}
          confidence={confidence}
          amountDifference={difference}
        />
        <ResolutionSuggestions
          match={match}
          onApplySuggestion={(suggestion) => {
            console.log('Apply suggestion:', suggestion);
            // TODO: Implement suggestion application
          }}
        />
        {sourceAmount !== 0 && (
          <PeriodComparison
            currentValue={sourceAmount}
            priorValue={undefined} // TODO: Fetch prior period value
            label="Source Amount"
          />
        )}
      </div>

      {/* Match Metadata */}
      <div className="border-t pt-4 space-y-2 text-xs text-gray-600">
        <div className="flex justify-between">
          <span>Match Type:</span>
          <span className="font-medium">{match.match_type}</span>
        </div>
        <div className="flex justify-between">
          <span>Algorithm:</span>
          <span className="font-medium">{match.match_algorithm || 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span>Exception Tier:</span>
          <span className="font-medium">{match.exception_tier || 'Not classified'}</span>
        </div>
        <div className="flex justify-between">
          <span>Status:</span>
          <span className="font-medium">{match.status}</span>
        </div>
        {match.reviewed_at && (
          <div className="flex justify-between">
            <span>Reviewed:</span>
            <span className="font-medium">
              {new Date(match.reviewed_at).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

