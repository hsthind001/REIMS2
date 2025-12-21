/**
 * XAI Explanation Component
 * 
 * Displays explainable AI insights for anomalies:
 * - SHAP feature importance charts
 * - LIME explanation display
 * - Root cause analysis
 * - Recommended actions
 */

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { AlertCircle, Lightbulb, TrendingUp, TrendingDown, Activity, FileText, CheckCircle } from 'lucide-react'
import { anomaliesService, AnomalyExplanation } from '../../lib/anomalies'

interface XAIExplanationProps {
  anomalyId: number
  autoLoad?: boolean
  className?: string
}

const ROOT_CAUSE_ICONS = {
  trend_break: TrendingUp,
  seasonal_deviation: Activity,
  outlier: AlertCircle,
  cross_account_inconsistency: FileText,
  volatility_spike: TrendingDown,
  missing_data: AlertCircle,
}

const ROOT_CAUSE_COLORS = {
  trend_break: '#3b82f6',
  seasonal_deviation: '#10b981',
  outlier: '#ef4444',
  cross_account_inconsistency: '#f59e0b',
  volatility_spike: '#8b5cf6',
  missing_data: '#6b7280',
}

export function XAIExplanation({ anomalyId, autoLoad = true, className = '' }: XAIExplanationProps) {
  const [explanation, setExplanation] = useState<AnomalyExplanation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (autoLoad) {
      loadExplanation()
    }
  }, [anomalyId, autoLoad])

  const loadExplanation = async () => {
    setLoading(true)
    setError(null)

    try {
      const existing = await anomaliesService.getExplanation(anomalyId)
      if (existing) {
        setExplanation(existing)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load explanation')
    } finally {
      setLoading(false)
    }
  }

  const generateExplanation = async () => {
    setGenerating(true)
    setError(null)

    try {
      const newExplanation = await anomaliesService.generateExplanation(anomalyId)
      setExplanation(newExplanation)
    } catch (err: any) {
      setError(err.message || 'Failed to generate explanation')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading explanation...</span>
        </div>
      </div>
    )
  }

  if (!explanation && !error) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="text-center py-8">
          <Lightbulb className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Explanation Available</h3>
          <p className="text-gray-600 mb-4">Generate an AI-powered explanation for this anomaly</p>
          <button
            onClick={generateExplanation}
            disabled={generating}
            className={`
              px-4 py-2 rounded-lg font-medium transition-all
              ${generating
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
              }
            `}
          >
            {generating ? 'Generating...' : 'Generate Explanation'}
          </button>
        </div>
      </div>
    )
  }

  if (error && !explanation) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle size={20} />
            <span className="font-medium">Error loading explanation</span>
          </div>
          <p className="text-red-600 text-sm mt-2">{error}</p>
          <button
            onClick={generateExplanation}
            disabled={generating}
            className="mt-3 px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-all"
          >
            {generating ? 'Generating...' : 'Try Generating New Explanation'}
          </button>
        </div>
      </div>
    )
  }

  if (!explanation) return null

  const RootCauseIcon = ROOT_CAUSE_ICONS[explanation.root_cause_type as keyof typeof ROOT_CAUSE_ICONS] || AlertCircle
  const rootCauseColor = ROOT_CAUSE_COLORS[explanation.root_cause_type as keyof typeof ROOT_CAUSE_COLORS] || '#6b7280'

  // Prepare SHAP values for chart
  const shapData = explanation.shap_values
    ? Object.entries(explanation.shap_values)
        .map(([feature, value]) => ({
          feature: feature.length > 20 ? feature.substring(0, 20) + '...' : feature,
          value: Math.abs(Number(value)),
          originalValue: Number(value),
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 10) // Top 10 features
    : []

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-yellow-500" />
          AI Explanation
        </h3>
        <button
          onClick={generateExplanation}
          disabled={generating}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {generating ? 'Regenerating...' : 'Regenerate'}
        </button>
      </div>

      {/* Root Cause Analysis */}
      <div className="mb-6">
        <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg border-l-4" style={{ borderLeftColor: rootCauseColor }}>
          <RootCauseIcon className="h-5 w-5 mt-0.5" style={{ color: rootCauseColor }} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                {explanation.root_cause_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">{explanation.root_cause_description}</p>
          </div>
        </div>
      </div>

      {/* Natural Language Explanation */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Explanation</h4>
        <p className="text-gray-700 text-sm leading-relaxed bg-blue-50 p-4 rounded-lg border border-blue-100">
          {explanation.natural_language_explanation}
        </p>
      </div>

      {/* SHAP Feature Importance Chart */}
      {shapData.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">Feature Importance (SHAP Values)</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={shapData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="feature" type="category" width={120} />
              <Tooltip
                formatter={(value: number, name: string, props: any) => [
                  `${props.payload.originalValue > 0 ? '+' : ''}${props.payload.originalValue.toFixed(4)}`,
                  'SHAP Value',
                ]}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {shapData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.originalValue > 0 ? '#ef4444' : '#10b981'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-500 mt-2">
            Red bars indicate features that increase anomaly score, green bars decrease it.
          </p>
        </div>
      )}

      {/* LIME Explanation */}
      {explanation.lime_explanation && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Local Explanation (LIME)</h4>
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
              {typeof explanation.lime_explanation === 'string'
                ? explanation.lime_explanation
                : JSON.stringify(explanation.lime_explanation, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Recommended Actions */}
      {explanation.action_suggestions && explanation.action_suggestions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            Recommended Actions
          </h4>
          <ul className="space-y-2">
            {explanation.action_suggestions.map((action, index) => (
              <li
                key={index}
                className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-100"
              >
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-gray-700">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

