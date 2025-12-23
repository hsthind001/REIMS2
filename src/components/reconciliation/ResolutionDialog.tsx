/**
 * Resolution Dialog Component
 * 
 * Modal dialog for resolving reconciliation discrepancies.
 * Provides options to accept PDF value, accept DB value, manually adjust, or ignore.
 */

import { useState } from 'react';
import { X, Check, XCircle, Edit, EyeOff } from 'lucide-react';
import type { ComparisonRecord, ResolutionRequest } from '../../lib/reconciliation';
import { reconciliationService } from '../../lib/reconciliation';

interface ResolutionDialogProps {
  record: ComparisonRecord;
  isOpen: boolean;
  onClose: () => void;
  onResolved: () => void;
}

export function ResolutionDialog({ record, isOpen, onClose, onResolved }: ResolutionDialogProps) {
  const [action, setAction] = useState<'accept_pdf' | 'accept_db' | 'manual_entry' | 'ignore'>('accept_pdf');
  const [manualValue, setManualValue] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !record.id) {
    return null;
  }

  const handleSubmit = async () => {
    if (!record.id) {
      setError('Difference ID is missing');
      return;
    }

    // Validate reason is provided
    if (!reason.trim()) {
      setError('Please provide a reason for this resolution');
      return;
    }

    // Validate manual entry if selected
    if (action === 'manual_entry') {
      if (!manualValue.trim()) {
        setError('Please enter a value for manual entry');
        return;
      }
      const numValue = parseFloat(manualValue);
      if (isNaN(numValue)) {
        setError('Please enter a valid number');
        return;
      }
    }

    try {
      setLoading(true);
      setError(null);

      const resolution: ResolutionRequest = {
        action,
        reason: reason.trim(),
        ...(action === 'manual_entry' ? { new_value: parseFloat(manualValue) } : {})
      };

      await reconciliationService.resolveDifference(record.id, resolution);
      
      // Success - close dialog and refresh
      onResolved();
      onClose();
      
      // Reset form
      setAction('accept_pdf');
      setManualValue('');
      setReason('');
    } catch (err: any) {
      console.error('Failed to resolve difference:', err);
      setError(err.message || 'Failed to resolve difference. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number | null) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const getMatchStatusColor = (status: string) => {
    switch (status) {
      case 'exact':
        return 'text-green-600 bg-green-50';
      case 'tolerance':
        return 'text-yellow-600 bg-yellow-50';
      case 'mismatch':
        return 'text-red-600 bg-red-50';
      case 'missing_pdf':
        return 'text-gray-600 bg-gray-50';
      case 'missing_db':
        return 'text-purple-600 bg-purple-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getMatchStatusLabel = (status: string) => {
    switch (status) {
      case 'exact':
        return 'Exact Match';
      case 'tolerance':
        return 'Within Tolerance';
      case 'mismatch':
        return 'Mismatch';
      case 'missing_pdf':
        return 'Missing in PDF';
      case 'missing_db':
        return 'Missing in DB';
      default:
        return status;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Resolve Discrepancy</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Record Information */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <div>
              <div className="text-sm text-gray-600">Account Code</div>
              <div className="font-semibold">{record.account_code}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Account Name</div>
              <div className="font-medium">{record.account_name}</div>
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="text-sm text-gray-600">PDF Value</div>
                <div className="font-semibold text-blue-600">
                  {formatCurrency(record.pdf_value)}
                </div>
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-600">Database Value</div>
                <div className="font-semibold text-green-600">
                  {formatCurrency(record.db_value)}
                </div>
              </div>
            </div>
            {record.difference !== null && (
              <div className="flex gap-4">
                <div className="flex-1">
                  <div className="text-sm text-gray-600">Difference</div>
                  <div className={`font-semibold ${
                    Math.abs(record.difference) > 0 ? 'text-red-600' : 'text-green-600'
                  }`}>
                    {formatCurrency(record.difference)}
                  </div>
                </div>
                {record.difference_percent !== null && (
                  <div className="flex-1">
                    <div className="text-sm text-gray-600">Difference %</div>
                    <div className={`font-semibold ${
                      Math.abs(record.difference_percent) > 1 ? 'text-red-600' : 'text-yellow-600'
                    }`}>
                      {record.difference_percent.toFixed(2)}%
                    </div>
                  </div>
                )}
              </div>
            )}
            <div>
              <div className="text-sm text-gray-600">Match Status</div>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getMatchStatusColor(record.match_status)}`}>
                {getMatchStatusLabel(record.match_status)}
              </span>
            </div>
          </div>

          {/* Resolution Action */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Resolution Action
            </label>
            <div className="space-y-2">
              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="action"
                  value="accept_pdf"
                  checked={action === 'accept_pdf'}
                  onChange={(e) => setAction(e.target.value as any)}
                  className="mr-3"
                  disabled={loading || record.pdf_value === null}
                />
                <div className="flex-1">
                  <div className="font-medium flex items-center gap-2">
                    <Check className="w-4 h-4 text-blue-600" />
                    Accept PDF Value
                  </div>
                  <div className="text-sm text-gray-600">
                    Update database to match PDF: {formatCurrency(record.pdf_value)}
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="action"
                  value="accept_db"
                  checked={action === 'accept_db'}
                  onChange={(e) => setAction(e.target.value as any)}
                  className="mr-3"
                  disabled={loading || record.db_value === null}
                />
                <div className="flex-1">
                  <div className="font-medium flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-600" />
                    Accept Database Value
                  </div>
                  <div className="text-sm text-gray-600">
                    Keep current database value: {formatCurrency(record.db_value)}
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="action"
                  value="manual_entry"
                  checked={action === 'manual_entry'}
                  onChange={(e) => setAction(e.target.value as any)}
                  className="mr-3"
                  disabled={loading}
                />
                <div className="flex-1">
                  <div className="font-medium flex items-center gap-2">
                    <Edit className="w-4 h-4 text-purple-600" />
                    Manual Entry
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Enter value"
                      value={manualValue}
                      onChange={(e) => setManualValue(e.target.value)}
                      className="w-full px-2 py-1 border rounded text-sm"
                      disabled={loading || action !== 'manual_entry'}
                    />
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="action"
                  value="ignore"
                  checked={action === 'ignore'}
                  onChange={(e) => setAction(e.target.value as any)}
                  className="mr-3"
                  disabled={loading}
                />
                <div className="flex-1">
                  <div className="font-medium flex items-center gap-2">
                    <EyeOff className="w-4 h-4 text-gray-600" />
                    Ignore Difference
                  </div>
                  <div className="text-sm text-gray-600">
                    Mark as resolved without making changes
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why you're choosing this resolution..."
              className="w-full px-3 py-2 border rounded-lg resize-none"
              rows={3}
              disabled={loading}
              required
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-sm text-red-600">{error}</div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              disabled={loading || !reason.trim() || (action === 'manual_entry' && !manualValue.trim())}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Resolving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Resolve
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

