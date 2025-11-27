/**
 * Anomalies Service
 * 
 * API calls for anomaly field coordinates
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

export const anomaliesService = {
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
  }
}
