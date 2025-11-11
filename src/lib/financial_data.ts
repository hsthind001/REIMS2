import { api } from './api'

export interface FinancialDataItem {
  id: number
  account_code: string
  account_name: string
  amounts: {
    amount?: number
    period_amount?: number
    ytd_amount?: number
    monthly_rent?: number
  }
  line_number: number | null
  is_subtotal: boolean
  is_total: boolean
  extraction_confidence: number
  match_confidence: number
  match_strategy: string
  match_strategy_label: string
  match_strategy_description: string
  severity: 'critical' | 'warning' | 'excellent'
  needs_review: boolean
  reviewed: boolean
  review_notes: string | null
  page_number: number | null
}

export interface FinancialDataResponse {
  upload_id: number
  property_code: string
  property_name: string
  period_year: number
  period_month: number
  document_type: string
  extraction_status: string
  total_items: number
  items: FinancialDataItem[]
  skip: number
  limit: number
}

export interface FinancialDataSummary {
  upload_id: number
  total_items: number
  by_severity: {
    critical: number
    warning: number
    excellent: number
  }
  by_match_strategy: Record<string, number>
  avg_extraction_confidence: number
  avg_match_confidence: number
  needs_review_count: number
  reviewed_count: number
  unreviewed_count: number
}

export const financialDataService = {
  /**
   * Get financial data for a specific upload
   */
  getFinancialData: async (
    uploadId: number,
    params?: {
      filter_needs_review?: boolean
      filter_critical?: boolean
      skip?: number
      limit?: number
    }
  ): Promise<FinancialDataResponse> => {
    const queryParams = new URLSearchParams()
    if (params?.filter_needs_review !== undefined) {
      queryParams.append('filter_needs_review', String(params.filter_needs_review))
    }
    if (params?.filter_critical !== undefined) {
      queryParams.append('filter_critical', String(params.filter_critical))
    }
    if (params?.skip !== undefined) {
      queryParams.append('skip', String(params.skip))
    }
    if (params?.limit !== undefined) {
      queryParams.append('limit', String(params.limit))
    }

    return await api.get<FinancialDataResponse>(`/financial-data/${uploadId}?${queryParams.toString()}`)
  },

  /**
   * Get summary statistics for financial data
   */
  getSummary: async (uploadId: number): Promise<FinancialDataSummary> => {
    return await api.get<FinancialDataSummary>(`/financial-data/${uploadId}/summary`)
  }
}

