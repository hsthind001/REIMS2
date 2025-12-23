/**
 * Learned Patterns List Component
 * 
 * Displays learned patterns from active learning:
 * - Pattern details (account code, anomaly type, confidence)
 * - Auto-suppression status
 * - Pattern confidence badges
 */

import { useState, useEffect } from 'react'
import { Brain, Shield, ShieldOff, TrendingUp, AlertCircle } from 'lucide-react'
import { anomaliesService, type LearnedPattern } from '../../lib/anomalies'

interface LearnedPatternsListProps {
  propertyId: number
  activeOnly?: boolean
  className?: string
}

export function LearnedPatternsList({ propertyId, activeOnly = true, className = '' }: LearnedPatternsListProps) {
  const [patterns, setPatterns] = useState<LearnedPattern[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPatterns()
  }, [propertyId, activeOnly])

  const loadPatterns = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await anomaliesService.getLearnedPatterns(propertyId, activeOnly)
      setPatterns(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load learned patterns')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading patterns...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle size={20} />
            <span className="font-medium">Error loading patterns</span>
          </div>
          <p className="text-red-600 text-sm mt-2">{error}</p>
        </div>
      </div>
    )
  }

  if (patterns.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="text-center py-8">
          <Brain className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Learned Patterns</h3>
          <p className="text-gray-600 text-sm">
            Patterns will appear here as the system learns from your feedback.
          </p>
        </div>
      </div>
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'bg-green-100 text-green-800 border-green-300'
    if (confidence >= 0.75) return 'bg-blue-100 text-blue-800 border-blue-300'
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    return 'bg-gray-100 text-gray-800 border-gray-300'
  }

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.9) return 'Very High'
    if (confidence >= 0.75) return 'High'
    if (confidence >= 0.6) return 'Medium'
    return 'Low'
  }

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-500" />
          Learned Patterns
        </h3>
        <span className="text-sm text-gray-500">
          {patterns.length} {activeOnly ? 'active' : ''} pattern{patterns.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-3">
        {patterns.map((pattern) => (
          <div
            key={pattern.id}
            className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-all"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium text-gray-900">{pattern.account_code}</span>
                  <span className="text-sm text-gray-500">•</span>
                  <span className="text-sm text-gray-600">{pattern.anomaly_type.replace(/_/g, ' ')}</span>
                  <span className="text-sm text-gray-500">•</span>
                  <span className="text-sm text-gray-600">{pattern.pattern_type.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded border ${getConfidenceColor(pattern.confidence)}`}
                  >
                    {getConfidenceLabel(pattern.confidence)} Confidence ({Math.round(pattern.confidence * 100)}%)
                  </span>
                  <span className="text-xs text-gray-500">
                    Seen {pattern.occurrence_count} time{pattern.occurrence_count !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {pattern.auto_suppress ? (
                  <div className="flex items-center gap-1 px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-medium">
                    <Shield size={14} />
                    Auto-Suppress
                  </div>
                ) : (
                  <div className="flex items-center gap-1 px-2 py-1 bg-gray-50 text-gray-600 rounded text-xs font-medium">
                    <ShieldOff size={14} />
                    Manual Review
                  </div>
                )}
              </div>
            </div>

            {/* Confidence Progress Bar */}
            <div className="mt-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-600">Pattern Confidence</span>
                <span className="text-xs font-medium text-gray-900">
                  {Math.round(pattern.confidence * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    pattern.confidence >= 0.9
                      ? 'bg-green-500'
                      : pattern.confidence >= 0.75
                      ? 'bg-blue-500'
                      : pattern.confidence >= 0.6
                      ? 'bg-yellow-500'
                      : 'bg-gray-400'
                  }`}
                  style={{ width: `${pattern.confidence * 100}%` }}
                />
              </div>
            </div>

            {/* Pattern Details */}
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>Pattern ID: {pattern.id}</span>
                <span>•</span>
                <span>
                  Created: {new Date(pattern.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {patterns.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <TrendingUp size={16} />
            <span>
              These patterns help the system automatically suppress known false positives and improve detection accuracy.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

