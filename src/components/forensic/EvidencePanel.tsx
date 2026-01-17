/**
 * Evidence Panel Component
 * 
 * Right panel showing side-by-side values, computed formula, PDF links, and actions
 */
import { FileText, ExternalLink, CheckCircle, XCircle,  Settings,
  AlertTriangle
} from 'lucide-react';
import { Card, Button } from '../design-system';
import { useState } from 'react';
import type { ForensicMatch, ForensicDiscrepancy } from '../../lib/forensic_reconciliation';
import WhyFlaggedCard from './WhyFlaggedCard';
import ResolutionSuggestions from './ResolutionSuggestions';
import PeriodComparison from './PeriodComparison';
import PDFSnippetViewer from './PDFSnippetViewer';
import RuleFailureDetail from './RuleFailureDetail';

interface EvidencePanelProps {
  match?: ForensicMatch | null;
  discrepancy?: ForensicDiscrepancy | null;
  onApprove?: (matchId: number) => void;
  onReject?: (matchId: number, reason: string) => void;
  onRemap?: (matchId: number, newMapping: any) => void;
  onAddNote?: (matchId: number, note: string) => void;
  onCreateTask?: (matchId: number, task: any) => void;
}

export default function EvidencePanel({ match, discrepancy, onApprove, onReject, onRemap, onAddNote, onCreateTask }: EvidencePanelProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'document' | 'history'>('details');

  if (discrepancy && !match) {
    return <RuleFailureDetail discrepancy={discrepancy} />;
  }

  if (!match) {
    return (
      <Card className="h-full flex items-center justify-center p-8 bg-gray-50 border-dashed">
        <div className="text-center text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">Select an item to view evidence</p>
          <p className="text-sm mt-1">Choose a match or discrepancy from the queue</p>
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

      {/* PDF Links / Snippets */}
      <div className="space-y-4">
        {/* Source Snippet */}
        {(match as any).source_coordinates ? (
            <PDFSnippetViewer
                uploadId={(match as any).source_coordinates.upload_id}
                bbox={(match as any).source_coordinates.bbox}
                page={(match as any).source_coordinates.page}
                label="Source Document"
                className="bg-white shadow-sm"
            />
        ) : (
            <Button
            variant="secondary"
            size="sm"
            className="w-full"
            icon={<ExternalLink className="w-4 h-4" />}
            onClick={() => {
                console.log('Open PDF for source document');
            }}
            >
            View Source PDF
            </Button>
        )}

        {/* Target Snippet */}
        {(match as any).target_coordinates ? (
            <PDFSnippetViewer
                uploadId={(match as any).target_coordinates.upload_id}
                bbox={(match as any).target_coordinates.bbox}
                page={(match as any).target_coordinates.page}
                label="Target Document"
                className="bg-white shadow-sm"
            />
        ) : (
            <Button
            variant="secondary"
            size="sm"
            className="w-full"
            icon={<ExternalLink className="w-4 h-4" />}
            onClick={() => {
                console.log('Open PDF for target document');
            }}
            >
            View Target PDF
            </Button>
        )}
      </div>

      {/* Actions */}
      <div className="border-t pt-4 space-y-2">
        <Button
          variant="success"
          className="w-full"
          icon={<CheckCircle className="w-4 h-4" />}
          disabled={!onApprove}
          onClick={() => onApprove && onApprove(match.id)}
        >
          Approve Match
        </Button>
        <Button
          variant="danger"
          className="w-full"
          icon={<XCircle className="w-4 h-4" />}
          disabled={!onReject}
          onClick={() => onReject && onReject(match.id, 'Rejected from evidence panel')}
        >
          Reject Match
        </Button>
        {onRemap && (
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              const newCode = window.prompt("Enter new target account code:");
              if (newCode) {
                 onRemap(match.id, { target_account_code: newCode });
              }
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
              const note = window.prompt("Enter note:");
              if (note) {
                  onAddNote(match.id, note);
              }
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
              const title = window.prompt("Enter task title:");
              if (title) {
                  onCreateTask(match.id, { title, status: 'pending' });
              }
            }}
          >
            Create Task
          </Button>
        )}
      </div>

      {/* Explainability Section */}
      <div className="border-t pt-4 space-y-4">
        <WhyFlaggedCard
          reasons={match.reasons || []}
          matchType={match.match_type}
          confidence={confidence}
          amountDifference={difference}
        />
        <ResolutionSuggestions
          match={match}
          onApplySuggestion={(suggestion) => {
            if (suggestion.type === 'ignore_variance') {
                if (confirm(`Confirm ignoring variance of ${suggestion.description}?`)) {
                    // In a real app, this calls api.resolveDiscrepancy
                    console.log('Resolving as immaterial:', suggestion);
                    alert('Difference marked as immaterial.');
                }
            } else if (suggestion.type === 'journal_entry') {
                // In a real app, this opens a Journal Entry modal
                console.log('Opening JE modal for:', suggestion);
                alert(`Opening Journal Entry Dialog\n\nAction: ${suggestion.suggested_action}\nReason: ${suggestion.description}`);
            } else if (suggestion.type === 'account_mapping') {
                 console.log('Opening Remap dialog:', suggestion);
                 alert(`Opening Remap Dialog\n\n${suggestion.suggested_action}`);
            } else {
                console.log('Applied:', suggestion);
            }
          }}
        />
        {sourceAmount !== 0 && (
          <PeriodComparison
            currentValue={sourceAmount}
            priorValue={match.prior_period_amount}
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

