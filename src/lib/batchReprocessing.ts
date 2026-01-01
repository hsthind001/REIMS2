/**
 * Batch Reprocessing Service
 * 
 * API integration for batch reprocessing jobs
 */

import { api } from './api'

export interface BatchReprocessingJob {
  id: number
  job_name: string
  status: 'queued' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
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
  extraction_status_filter?: string
}

export interface BatchJobCreateResponse {
  job_id: number
  job_name?: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  total_documents: number
  created_at: string
  task_id?: string
}

export interface BatchJobStatusResponse {
  job_id: number
  job_name?: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress_pct: number
  total_documents: number
  processed_documents: number
  successful_count: number
  failed_count: number
  skipped_count: number
  started_at?: string
  completed_at?: string
  estimated_completion_at?: string
  celery_task_id?: string
  results_summary?: any
}

export const batchReprocessingService = {
  /**
   * Create a new batch reprocessing job
   */
  async createJob(request: BatchJobCreateRequest): Promise<BatchJobCreateResponse> {
    try {
      return await api.post<BatchJobCreateResponse>('/batch-reprocessing/reprocess', request)
    } catch (error: any) {
      console.error('Failed to create batch job:', error)
      throw new Error(error.message || 'Failed to create batch job')
    }
  },

  /**
   * Get batch job status
   */
  async getJobStatus(jobId: number): Promise<BatchReprocessingJob> {
    try {
      const job = await api.get<BatchJobStatusResponse>(`/batch-reprocessing/jobs/${jobId}`)
      return {
        id: job.job_id,
        job_name: job.job_name || `Batch Job ${job.job_id}`,
        status: job.status,
        total_documents: job.total_documents,
        processed_documents: job.processed_documents,
        successful_count: job.successful_count,
        failed_count: job.failed_count,
        skipped_count: job.skipped_count,
        progress_pct: job.progress_pct,
        started_at: job.started_at,
        completed_at: job.completed_at,
        estimated_completion_at: job.estimated_completion_at,
        celery_task_id: job.celery_task_id,
        results_summary: job.results_summary
      }
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
      await api.post(`/batch-reprocessing/jobs/${jobId}/cancel`, {})
    } catch (error: any) {
      console.error('Failed to cancel batch job:', error)
      throw new Error(error.message || 'Failed to cancel batch job')
    }
  },

  /**
   * List all batch reprocessing jobs
   */
  async listJobs(jobType?: string): Promise<BatchReprocessingJob[]> {
    try {
      const params = jobType ? `?job_type=${encodeURIComponent(jobType)}` : ''
      return await api.get<BatchReprocessingJob[]>(`/batch-reprocessing/jobs${params}`)
    } catch (error: any) {
      console.error('Failed to list batch jobs:', error)
      throw new Error(error.message || 'Failed to list batch jobs')
    }
  },
}
