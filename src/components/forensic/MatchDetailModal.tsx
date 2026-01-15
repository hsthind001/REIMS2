/**
 * Match Detail Modal Component
 *
 * Side-by-side comparison of source and target values with algorithm explanation
 */

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../design-system';
import type { ForensicMatch } from '../../lib/forensic_reconciliation';
import PDFSnippetViewer from './PDFSnippetViewer';
import WhyFlaggedCard from './WhyFlaggedCard';

interface MatchDetailModalProps {
  match: ForensicMatch;
  onClose: () => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
}

export default function MatchDetailModal({
  match,
  onClose,
  onApprove,
  onReject
}: MatchDetailModalProps) {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  // Handle ESC key to close modal and lock body scroll
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const handleReject = () => {
    if (!rejectReason.trim()) {
      alert('Please provide a rejection reason');
      return;
    }
    onReject(rejectReason);
  };

  const modalContent = (
    <div
      className="fixed inset-0 z-[60] p-4"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(4px)'
      }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        style={{
          position: 'relative',
          backgroundColor: '#ffffff',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between" style={{ backgroundColor: '#ffffff', zIndex: 10 }}>
          <h2 className="text-xl font-bold text-gray-900">Match Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full p-1 transition-colors"
            title="Close (or click outside)"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[calc(100vh-200px)] overflow-y-auto">
          {/* AI Explainability */}
          <WhyFlaggedCard
            reasons={match.reasons || []}
            matchType={match.match_type}
            confidence={match.confidence_score}
            amountDifference={match.amount_difference}
          />
          
          {/* Match Information */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Match ID</h3>
              <p className="text-lg font-semibold text-gray-900">#{match.id}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Match Type</h3>
              <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
                match.match_type === 'exact' ? 'bg-green-100 text-green-800' :
                match.match_type === 'fuzzy' ? 'bg-blue-100 text-blue-800' :
                match.match_type === 'calculated' ? 'bg-purple-100 text-purple-800' :
                'bg-amber-100 text-amber-800'
              }`}>
                {match.match_type}
              </span>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Confidence Score</h3>
              <p className="text-lg font-semibold text-gray-900">{match.confidence_score.toFixed(2)}%</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
              <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
                match.status === 'approved' ? 'bg-green-100 text-green-800' :
                match.status === 'rejected' ? 'bg-red-100 text-red-800' :
                match.status === 'modified' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {match.status}
              </span>
            </div>
          </div>

          {/* Side-by-Side Comparison */}
          <div className="grid grid-cols-2 gap-6">
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Source Document</h3>
              {(match as any).source_coordinates ? (
                <PDFSnippetViewer
                  uploadId={(match as any).source_coordinates.upload_id}
                  bbox={(match as any).source_coordinates.bbox}
                  page={(match as any).source_coordinates.page}
                  label="Source Snippet"
                  className="bg-gray-50 mb-4"
                />
              ) : null}
              <div className="space-y-2">
                <div>
                  <span className="text-xs text-gray-500">Type:</span>
                  <span className="ml-2 font-medium">{match.source_document_type}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Record ID:</span>
                  <span className="ml-2 font-medium">{match.source_record_id}</span>
                </div>
                {match.source_amount !== undefined && (
                  <div>
                    <span className="text-xs text-gray-500">Amount:</span>
                    <span className="ml-2 font-semibold text-lg">
                      ${match.source_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Target Document</h3>
              {(match as any).target_coordinates ? (
                <PDFSnippetViewer
                  uploadId={(match as any).target_coordinates.upload_id}
                  bbox={(match as any).target_coordinates.bbox}
                  page={(match as any).target_coordinates.page}
                  label="Target Snippet"
                  className="bg-gray-50 mb-4"
                />
              ) : null}
              <div className="space-y-2">
                <div>
                  <span className="text-xs text-gray-500">Type:</span>
                  <span className="ml-2 font-medium">{match.target_document_type}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Record ID:</span>
                  <span className="ml-2 font-medium">{match.target_record_id}</span>
                </div>
                {match.target_amount !== undefined && (
                  <div>
                    <span className="text-xs text-gray-500">Amount:</span>
                    <span className="ml-2 font-semibold text-lg">
                      ${match.target_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Difference */}
          {match.amount_difference !== undefined && (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Difference</h3>
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-xs text-gray-500">Amount:</span>
                  <span className="ml-2 font-semibold text-lg">
                    ${Math.abs(match.amount_difference).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                {match.amount_difference_percent !== undefined && (
                  <div>
                    <span className="text-xs text-gray-500">Percent:</span>
                    <span className="ml-2 font-semibold text-lg">
                      {match.amount_difference_percent.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Algorithm Explanation */}
          {match.match_algorithm && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Match Algorithm</h3>
              <p className="text-sm text-gray-700">{match.match_algorithm}</p>
            </div>
          )}

          {/* Relationship Formula */}
          {match.relationship_formula && (
            <div className="border border-gray-200 rounded-lg p-4 bg-blue-50">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Relationship Formula</h3>
              <p className="text-sm font-mono text-blue-900">{match.relationship_formula}</p>
            </div>
          )}

          {/* Review Notes */}
          {match.review_notes && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Review Notes</h3>
              <p className="text-sm text-gray-700">{match.review_notes}</p>
              {match.reviewed_at && (
                <p className="text-xs text-gray-500 mt-2">
                  Reviewed at: {new Date(match.reviewed_at).toLocaleString()}
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          {match.status === 'pending' && (
            <div className="flex items-center gap-4 pt-4 border-t border-gray-200">
              <Button
                onClick={onApprove}
                variant="success"
                icon={<CheckCircle className="w-4 h-4" />}
              >
                Approve Match
              </Button>
              <Button
                onClick={() => setShowRejectInput(!showRejectInput)}
                variant="danger"
                icon={<XCircle className="w-4 h-4" />}
              >
                Reject Match
              </Button>
            </div>
          )}

          {showRejectInput && (
            <div className="border border-red-200 rounded-lg p-4 bg-red-50">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rejection Reason *
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                rows={3}
                placeholder="Explain why this match should be rejected..."
              />
              <div className="flex gap-2 mt-3">
                <Button
                  onClick={handleReject}
                  variant="danger"
                  size="sm"
                  disabled={!rejectReason.trim()}
                >
                  Confirm Reject
                </Button>
                <Button
                  onClick={() => {
                    setShowRejectInput(false);
                    setRejectReason('');
                  }}
                  variant="info"
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Render modal using portal to bypass parent container constraints
  return createPortal(modalContent, document.body);
}

