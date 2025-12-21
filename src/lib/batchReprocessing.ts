/**
 * Batch Reprocessing Service
 * 
 * API integration for batch reprocessing jobs
 */

import { api } from './api'

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

export interface BatchJobCreateRequest {
  job_name: string
  property_ids?: number[]
  date_range_start?: string
  date_range_end?: string
  document_types?: string[]
  extraction_status?: string
}

export const batchReprocessingService = {
  /**
   * Create a new batch reprocessing job
   */
  async createJob(request: BatchJobCreateRequest): Promise<BatchReprocessingJob> {
    try {
      return await api.post<BatchReprocessingJob>('/batch-reprocessing/', request)
    } catch (error: any) {
      console.error('Failed to create batch job:', error)
      throw new Error(error.message || 'Failed to create batch job')
    }
  },

  /**
   * Start a batch reprocessing job
   */
  async startJob(jobId: number): Promise<BatchReprocessingJob> {
    try {
      return await api.post<BatchReprocessingJob>(`/batch-reprocessing/${jobId}/start`, {})
    } catch (error: any) {
      console.error('Failed to start batch job:', error)
      throw new Error(error.message || 'Failed to start batch job')
    }
  },

  /**
   * Get batch job status
   */
  async getJobStatus(jobId: number): Promise<BatchReprocessingJob> {
    try {
      return await api.get<BatchReprocessingJob>(`/batch-reprocessing/${jobId}`)
    } catch (error: any) {
      console.error('Failed to get job status:', error)
      throw new Error(error.message || 'Failed to get job status')
    }
  },

  /**
   * Cancel a batch reprocessing job
   */
  async cancelJob(jobId: number): Promise<void> {
    try {
      await api.post(`/batch-reprocessing/${jobId}/cancel`, {})
    } catch (error: any) {
      console.error('Failed to cancel batch job:', error)
      throw new Error(error.message || 'Failed to cancel batch job')
    }
  },

  /**
   * List all batch reprocessing jobs
   */
  async listJobs(): Promise<BatchReprocessingJob[]> {
    try {
      return await api.get<BatchReprocessingJob[]>('/batch-reprocessing/jobs')
    } catch (error: any) {
      console.error('Failed to list batch jobs:', error)
      throw new Error(error.message || 'Failed to list batch jobs')
    }
  },
}

