/**
 * Anomalies Service
 * 
 * Complete API integration for world-class anomaly detection system
 */

import { api } from './api'

export interface FieldCoordinatesResponse {
  has_coordinates: boolean
  coordinates?: {
    x0: number
    y0: number
    x1: number
    y1: number
    page_number: number
  } | null
  pdf_url: string | null
  explanation: string
}

export interface Anomaly {
  id: number
  property_id: number
  account_code: string
  field_name?: string
  anomaly_type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  actual_value?: number
  expected_value?: number
  deviation?: number
  confidence_score?: number
  detected_at: string
  message?: string
  details?: any
  document_id?: number
  document_type?: string
  period_id?: number
  model_used?: string
  context_suppressed?: boolean
  suppression_reason?: string
}

export interface DetailedAnomalyResponse extends Anomaly {
  explanation?: {
    root_cause_type: string
    root_cause_description: string
    natural_language_explanation: string
    action_suggestions: string[]
    shap_values?: any
    lime_explanation?: any
  }
  pdf_coordinates?: FieldCoordinatesResponse
  similar_anomalies?: Array<{
    id: number
    detected_at: string
    actual_value?: number
    expected_value?: number
    severity: string
  }>
  feedback_stats?: {
    total_feedback: number
    true_positive_rate: number
    false_positive_rate: number
    recent_feedback: Array<{
      feedback_type: string
      created_at: string
      notes?: string
    }>
  }
  learned_patterns?: Array<{
    id: number
    account_code: string
    anomaly_type: string
    pattern_type: string
    confidence: number
    auto_suppress: boolean
  }>
  portfolio_context?: {
    percentile_rank: number
    benchmark_mean: number
    benchmark_median: number
    property_count: number
  }
}

export interface UncertainAnomaly {
  id: number
  property_id: number
  account_code: string
  field_name?: string
  anomaly_type: string
  severity: string
  actual_value?: number
  expected_value?: number
  confidence: number
  uncertainty_score: number
  days_since_detection: number
  feedback_count: number
  similar_anomalies_count: number
  detected_at: string
  message?: string
}

export interface AnomalyExplanation {
  root_cause_type: string
  root_cause_description: string
  natural_language_explanation: string
  action_suggestions: string[]
  shap_values?: any
  lime_explanation?: any
}

// Re-export types for better ES module compatibility
export type { 
  Anomaly,
  DetailedAnomalyResponse,
  UncertainAnomaly,
  AnomalyExplanation,
  AnomalyFeedback,
  LearnedPattern,
  PortfolioBenchmark,
  FieldCoordinatesResponse
}

export interface AnomalyFeedback {
  id: number
  anomaly_detection_id: number
  user_id: number
  feedback_type: 'true_positive' | 'false_positive' | 'needs_review'
  feedback_notes?: string
  feedback_confidence?: number
  business_context?: any
  created_at: string
}

export interface LearnedPattern {
  id: number
  property_id: number
  account_code: string
  anomaly_type: string
  pattern_type: string
  confidence: number
  occurrence_count: number
  auto_suppress: boolean
  created_at: string
}

export interface PortfolioBenchmark {
  account_code: string
  percentile_rank: number
  benchmark_mean: number
  benchmark_median: number
  benchmark_std: number
  property_count: number
  percentile_25: number
  percentile_75: number
  percentile_90: number
  percentile_95: number
}

export interface BatchReprocessingJob {
  id: number
  job_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  total_documents: number
  processed_documents: number
  successful_count: number
  failed_count: number
  skipped_count: number
  progress_pct: number
  started_at?: string
  completed_at?: string
  estimated_completion_at?: string
  celery_task_id?: string
  results_summary?: any
}

export const anomaliesService = {
  normalizeExplanation(raw: any): AnomalyExplanation {
    const shapSource = raw?.shap_feature_importance || raw?.shap_values
    const shapValues = shapSource && !Array.isArray(shapSource) ? shapSource : undefined
    const suggestions =
      Array.isArray(raw?.action_suggestions) ? raw.action_suggestions
      : Array.isArray(raw?.suggested_actions)
        ? raw.suggested_actions.map((item: any) => {
            if (typeof item === 'string') return item
            const action = item?.action ? String(item.action) : ''
            const description = item?.description ? String(item.description) : ''
            return [action, description].filter(Boolean).join(' — ')
          })
        : []

    return {
      root_cause_type: raw?.root_cause_type || 'unknown',
      root_cause_description: raw?.root_cause_description || 'No root cause description available.',
      natural_language_explanation: raw?.natural_language_explanation || raw?.root_cause_description || '',
      action_suggestions: suggestions,
      shap_values: shapValues,
      lime_explanation: raw?.lime_explanation,
    }
  },
  /**
   * Get field coordinates and PDF URL for an anomaly
   */
  async getFieldCoordinates(anomalyId: number): Promise<FieldCoordinatesResponse> {
    try {
      return await api.get<FieldCoordinatesResponse>(`/anomalies/${anomalyId}/field-coordinates`)
    } catch (error: any) {
      console.error('Failed to get field coordinates:', error)
      throw new Error(error.message || 'Failed to get field coordinates')
    }
  },

  /**
   * Get list of anomalies
   */
  async getAnomalies(params?: {
    property_id?: number
    account_code?: string
    severity?: string
    anomaly_type?: string
    limit?: number
    offset?: number
  }): Promise<Anomaly[]> {
    try {
      const queryParams = new URLSearchParams()
      if (params?.property_id) queryParams.append('property_id', params.property_id.toString())
      if (params?.account_code) queryParams.append('account_code', params.account_code)
      if (params?.severity) queryParams.append('severity', params.severity)
      if (params?.anomaly_type) queryParams.append('anomaly_type', params.anomaly_type)
      if (params?.limit) queryParams.append('limit', params.limit.toString())
      if (params?.offset) queryParams.append('offset', params.offset.toString())

      const url = `/anomalies${queryParams.toString() ? '?' + queryParams.toString() : ''}`
      return await api.get<Anomaly[]>(url)
    } catch (error: any) {
      console.error('Failed to get anomalies:', error)
      throw new Error(error.message || 'Failed to get anomalies')
    }
  },

  /**
   * Get detailed anomaly information (enhanced endpoint)
   */
  async getAnomalyDetailed(anomalyId: number): Promise<DetailedAnomalyResponse> {
    try {
      return await api.get<DetailedAnomalyResponse>(`/anomalies/${anomalyId}/detailed`)
    } catch (error: any) {
      console.error('Failed to get detailed anomaly:', error)
      throw new Error(error.message || 'Failed to get detailed anomaly')
    }
  },

  /**
   * Get uncertain anomalies (most needing feedback)
   */
  async getUncertainAnomalies(limit: number = 10): Promise<UncertainAnomaly[]> {
    try {
      return await api.get<UncertainAnomaly[]>(`/anomalies/uncertain?limit=${limit}`)
    } catch (error: any) {
      console.error('Failed to get uncertain anomalies:', error)
      throw new Error(error.message || 'Failed to get uncertain anomalies')
    }
  },

  /**
   * Generate XAI explanation for an anomaly
   */
  async generateExplanation(anomalyId: number): Promise<AnomalyExplanation> {
    try {
      const response = await api.post<any>(`/anomalies/${anomalyId}/explain`, {})
      return anomaliesService.normalizeExplanation(response)
    } catch (error: any) {
      console.error('Failed to generate explanation:', error)
      throw new Error(error.message || 'Failed to generate explanation')
    }
  },

  /**
   * Get existing explanation for an anomaly
   */
  async getExplanation(anomalyId: number): Promise<AnomalyExplanation | null> {
    try {
      const response = await api.get<any>(`/anomalies/${anomalyId}/explanation`)
      return anomaliesService.normalizeExplanation(response)
    } catch (error: any) {
      if (error.status === 404) return null
      console.error('Failed to get explanation:', error)
      throw new Error(error.message || 'Failed to get explanation')
    }
  },

  /**
   * Submit feedback for an anomaly
   */
  async submitFeedback(
    anomalyId: number,
    feedbackType: 'true_positive' | 'false_positive' | 'needs_review',
    feedbackNotes?: string,
    feedbackConfidence?: number,
    businessContext?: any
  ): Promise<AnomalyFeedback> {
    try {
      const params = new URLSearchParams()
      params.append('feedback_type', feedbackType)
      if (feedbackNotes) params.append('feedback_notes', feedbackNotes)
      if (feedbackConfidence !== undefined) params.append('feedback_confidence', feedbackConfidence.toString())
      if (businessContext) params.append('business_context', JSON.stringify(businessContext))

      return await api.post<AnomalyFeedback>(`/anomalies/${anomalyId}/feedback?${params.toString()}`, {})
    } catch (error: any) {
      console.error('Failed to submit feedback:', error)
      throw new Error(error.message || 'Failed to submit feedback')
    }
  },

  /**
   * Get feedback statistics for a property
   */
  async getFeedbackStats(propertyId: number, days: number = 90): Promise<any> {
    try {
      return await api.get(`/anomalies/property/${propertyId}/feedback-stats?days=${days}`)
    } catch (error: any) {
      console.error('Failed to get feedback stats:', error)
      throw new Error(error.message || 'Failed to get feedback stats')
    }
  },

  /**
   * Get learned patterns for a property
   */
  async getLearnedPatterns(propertyId: number, activeOnly: boolean = true): Promise<LearnedPattern[]> {
    try {
      return await api.get<LearnedPattern[]>(`/anomalies/property/${propertyId}/learned-patterns?active_only=${activeOnly}`)
    } catch (error: any) {
      console.error('Failed to get learned patterns:', error)
      throw new Error(error.message || 'Failed to get learned patterns')
    }
  },

  /**
   * Get property benchmark ranking
   */
  async getPropertyBenchmark(
    propertyId: number,
    accountCode: string,
    metricType: string = 'balance_sheet'
  ): Promise<PortfolioBenchmark> {
    try {
      return await api.get<PortfolioBenchmark>(`/anomalies/property/${propertyId}/benchmarks/${accountCode}?metric_type=${metricType}`)
    } catch (error: any) {
      console.error('Failed to get property benchmark:', error)
      throw new Error(error.message || 'Failed to get property benchmark')
    }
  },

  /**
   * Export anomalies to CSV
   */
  async exportAnomaliesCSV(params: {
    property_ids?: number[]
    date_start?: string
    date_end?: string
    severity?: string
    anomaly_type?: string
    account_codes?: string[]
    include_explanations?: boolean
    include_feedback?: boolean
    include_cross_property?: boolean
  }): Promise<Blob> {
    try {
      const queryParams = new URLSearchParams()
      if (params.property_ids) queryParams.append('property_ids', params.property_ids.join(','))
      if (params.date_start) queryParams.append('date_start', params.date_start)
      if (params.date_end) queryParams.append('date_end', params.date_end)
      if (params.severity) queryParams.append('severity', params.severity)
      if (params.anomaly_type) queryParams.append('anomaly_type', params.anomaly_type)
      if (params.account_codes) queryParams.append('account_codes', params.account_codes.join(','))
      if (params.include_explanations !== undefined) queryParams.append('include_explanations', params.include_explanations.toString())
      if (params.include_feedback !== undefined) queryParams.append('include_feedback', params.include_feedback.toString())
      if (params.include_cross_property !== undefined) queryParams.append('include_cross_property', params.include_cross_property.toString())

      const response = await fetch(`${api.baseURL}/anomalies/export/csv?${queryParams.toString()}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'text/csv',
        },
      })

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      return await response.blob()
    } catch (error: any) {
      console.error('Failed to export anomalies to CSV:', error)
      throw new Error(error.message || 'Failed to export anomalies to CSV')
    }
  },

  /**
   * Export anomalies to Excel
   */
  async exportAnomaliesExcel(params: {
    property_ids?: number[]
    date_start?: string
    date_end?: string
    severity?: string
    anomaly_type?: string
    account_codes?: string[]
    include_explanations?: boolean
    include_feedback?: boolean
    include_cross_property?: boolean
  }): Promise<Blob> {
    try {
      const queryParams = new URLSearchParams()
      if (params.property_ids) queryParams.append('property_ids', params.property_ids.join(','))
      if (params.date_start) queryParams.append('date_start', params.date_start)
      if (params.date_end) queryParams.append('date_end', params.date_end)
      if (params.severity) queryParams.append('severity', params.severity)
      if (params.anomaly_type) queryParams.append('anomaly_type', params.anomaly_type)
      if (params.account_codes) queryParams.append('account_codes', params.account_codes.join(','))
      if (params.include_explanations !== undefined) queryParams.append('include_explanations', params.include_explanations.toString())
      if (params.include_feedback !== undefined) queryParams.append('include_feedback', params.include_feedback.toString())
      if (params.include_cross_property !== undefined) queryParams.append('include_cross_property', params.include_cross_property.toString())

      const response = await fetch(`${api.baseURL}/anomalies/export/excel?${queryParams.toString()}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
      })

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      return await response.blob()
    } catch (error: any) {
      console.error('Failed to export anomalies to Excel:', error)
      throw new Error(error.message || 'Failed to export anomalies to Excel')
    }
  },

  /**
   * Export anomalies to JSON
   */
  async exportAnomaliesJSON(params: {
    property_ids?: number[]
    date_start?: string
    date_end?: string
    severity?: string
    anomaly_type?: string
    account_codes?: string[]
    include_explanations?: boolean
    include_feedback?: boolean
    include_cross_property?: boolean
  }): Promise<any> {
    try {
      const queryParams = new URLSearchParams()
      if (params.property_ids) queryParams.append('property_ids', params.property_ids.join(','))
      if (params.date_start) queryParams.append('date_start', params.date_start)
      if (params.date_end) queryParams.append('date_end', params.date_end)
      if (params.severity) queryParams.append('severity', params.severity)
      if (params.anomaly_type) queryParams.append('anomaly_type', params.anomaly_type)
      if (params.account_codes) queryParams.append('account_codes', params.account_codes.join(','))
      if (params.include_explanations !== undefined) queryParams.append('include_explanations', params.include_explanations.toString())
      if (params.include_feedback !== undefined) queryParams.append('include_feedback', params.include_feedback.toString())
      if (params.include_cross_property !== undefined) queryParams.append('include_cross_property', params.include_cross_property.toString())

      return await api.get(`/anomalies/export/json?${queryParams.toString()}`)
    } catch (error: any) {
      console.error('Failed to export anomalies to JSON:', error)
      throw new Error(error.message || 'Failed to export anomalies to JSON')
    }
  },

  /**
   * Trigger anomaly detection for a specific document upload
   * Useful for re-running detection after threshold changes or on older documents
   */
  async triggerAnomalyDetection(uploadId: number): Promise<{
    success: boolean
    upload_id: number
    document_type: string
    deleted_old_anomalies: number
    new_anomalies_detected: number
    message: string
  }> {
    try {
      return await api.post(`/anomalies/detect/${uploadId}`, {})
    } catch (error: any) {
      console.error('Failed to trigger anomaly detection:', error)
      throw new Error(error.message || 'Failed to trigger anomaly detection')
    }
  },
}
