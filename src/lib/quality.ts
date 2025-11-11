/**
 * Quality Service
 * 
 * API calls for quality metrics and assessments
 */

import { api } from './api'

export class QualityService {
  /**
   * Get quality metrics for a specific document upload
   */
  async getDocumentQuality(uploadId: number) {
    return api.get(`/quality/document/${uploadId}`)
  }
  
  /**
   * Get quality summary aggregated by property
   */
  async getPropertyQualitySummary(propertyCode?: string) {
    const params = propertyCode ? { property_code: propertyCode } : {}
    return api.get('/quality/summary', params)
  }
}

// Export singleton
export const qualityService = new QualityService()

