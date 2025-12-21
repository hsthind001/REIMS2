/**
 * Feedback Buttons Component
 * 
 * Provides user feedback interface for anomaly detection:
 * - Thumbs up/down buttons
 * - Dismiss button with reason dropdown
 * - Confidence slider
 * - Business context text area
 */

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, X, AlertCircle } from 'lucide-react'
import { anomaliesService } from '../../lib/anomalies'

interface FeedbackButtonsProps {
  anomalyId: number
  onFeedbackSubmitted?: () => void
  className?: string
}

export function FeedbackButtons({ anomalyId, onFeedbackSubmitted, className = '' }: FeedbackButtonsProps) {
  const [feedbackType, setFeedbackType] = useState<'true_positive' | 'false_positive' | 'needs_review' | null>(null)
  const [showDismissModal, setShowDismissModal] = useState(false)
  const [dismissReason, setDismissReason] = useState('')
  const [feedbackNotes, setFeedbackNotes] = useState('')
  const [feedbackConfidence, setFeedbackConfidence] = useState(80)
  const [businessContext, setBusinessContext] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleThumbsUp = async () => {
    setFeedbackType('true_positive')
    await submitFeedback('true_positive')
  }

  const handleThumbsDown = async () => {
    setFeedbackType('false_positive')
    await submitFeedback('false_positive')
  }

  const handleNeedsReview = () => {
    setFeedbackType('needs_review')
    setShowDismissModal(true)
  }

  const submitFeedback = async (type: 'true_positive' | 'false_positive' | 'needs_review') => {
    setSubmitting(true)
    setError(null)
    setSuccess(false)

    try {
      await anomaliesService.submitFeedback(
        anomalyId,
        type,
        feedbackNotes || undefined,
        feedbackConfidence / 100,
        businessContext ? { notes: businessContext } : undefined
      )

      setSuccess(true)
      setTimeout(() => {
        setSuccess(false)
        if (onFeedbackSubmitted) {
          onFeedbackSubmitted()
        }
      }, 2000)
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDismissSubmit = async () => {
    if (!dismissReason) {
      setError('Please select a reason for dismissing')
      return
    }

    await submitFeedback('needs_review')
    setShowDismissModal(false)
    setDismissReason('')
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Thumbs Up Button */}
      <button
        onClick={handleThumbsUp}
        disabled={submitting || success}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg transition-all
          ${feedbackType === 'true_positive' || success
            ? 'bg-green-100 text-green-700 border-2 border-green-300'
            : 'bg-gray-100 text-gray-700 hover:bg-green-50 hover:text-green-700 border-2 border-transparent'
          }
          ${submitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        title="Mark as correct detection (True Positive)"
      >
        <ThumbsUp size={18} />
        <span className="text-sm font-medium">Correct</span>
      </button>

      {/* Thumbs Down Button */}
      <button
        onClick={handleThumbsDown}
        disabled={submitting || success}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg transition-all
          ${feedbackType === 'false_positive' || success
            ? 'bg-red-100 text-red-700 border-2 border-red-300'
            : 'bg-gray-100 text-gray-700 hover:bg-red-50 hover:text-red-700 border-2 border-transparent'
          }
          ${submitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        title="Mark as incorrect detection (False Positive)"
      >
        <ThumbsDown size={18} />
        <span className="text-sm font-medium">Incorrect</span>
      </button>

      {/* Needs Review / Dismiss Button */}
      <button
        onClick={handleNeedsReview}
        disabled={submitting || success}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg transition-all
          ${feedbackType === 'needs_review' || success
            ? 'bg-yellow-100 text-yellow-700 border-2 border-yellow-300'
            : 'bg-gray-100 text-gray-700 hover:bg-yellow-50 hover:text-yellow-700 border-2 border-transparent'
          }
          ${submitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        title="Mark as needs review"
      >
        <AlertCircle size={18} />
        <span className="text-sm font-medium">Review</span>
      </button>

      {/* Success Message */}
      {success && (
        <div className="flex items-center gap-2 text-green-600 text-sm font-medium animate-fade-in">
          <span>✓ Feedback submitted!</span>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-red-600 text-sm font-medium">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Dismiss Modal */}
      {showDismissModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Dismiss Anomaly</h3>
              <button
                onClick={() => {
                  setShowDismissModal(false)
                  setDismissReason('')
                  setError(null)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Dismiss Reason Dropdown */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for Dismissal *
                </label>
                <select
                  value={dismissReason}
                  onChange={(e) => setDismissReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select a reason...</option>
                  <option value="expected_variation">Expected variation (seasonal, one-time event)</option>
                  <option value="data_entry_error">Data entry error (will be corrected)</option>
                  <option value="business_context">Valid business context (explained in notes)</option>
                  <option value="calculation_method">Different calculation method used</option>
                  <option value="timing_difference">Timing difference (accrual vs cash)</option>
                  <option value="other">Other (explain in notes)</option>
                </select>
              </div>

              {/* Confidence Slider */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Level: {feedbackConfidence}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={feedbackConfidence}
                  onChange={(e) => setFeedbackConfidence(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Not Sure</span>
                  <span>Very Confident</span>
                </div>
              </div>

              {/* Business Context Text Area */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Business Context (Optional)
                </label>
                <textarea
                  value={businessContext}
                  onChange={(e) => setBusinessContext(e.target.value)}
                  placeholder="Provide additional context about why this anomaly should be dismissed..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Feedback Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Additional Notes (Optional)
                </label>
                <textarea
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Any additional notes about this feedback..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Error Display */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleDismissSubmit}
                  disabled={submitting || !dismissReason}
                  className={`
                    flex-1 px-4 py-2 rounded-lg font-medium transition-all
                    ${submitting || !dismissReason
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-yellow-500 text-white hover:bg-yellow-600'
                    }
                  `}
                >
                  {submitting ? 'Submitting...' : 'Submit Feedback'}
                </button>
                <button
                  onClick={() => {
                    setShowDismissModal(false)
                    setDismissReason('')
                    setError(null)
                  }}
                  className="px-4 py-2 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}

