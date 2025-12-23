/**
 * Batch Reprocessing Form Component
 * 
 * Create and monitor batch reprocessing jobs:
 * - Job creation form
 * - Job status table with progress
 * - Cancel/retry buttons
 * - WebSocket real-time updates
 */

import { useState, useEffect, useRef } from 'react'
import { Play, X, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react'
import { batchReprocessingService, type BatchReprocessingJob, type BatchJobCreateRequest } from '../../lib/batchReprocessing'

interface BatchReprocessingFormProps {
  className?: string
}

export function BatchReprocessingForm({ className = '' }: BatchReprocessingFormProps) {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [jobs, setJobs] = useState<BatchReprocessingJob[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  // Form state
  const [jobName, setJobName] = useState('')
  const [propertyIds, setPropertyIds] = useState('')
  const [dateStart, setDateStart] = useState('')
  const [dateEnd, setDateEnd] = useState('')
  const [documentTypes, setDocumentTypes] = useState('')

  // WebSocket connections
  const wsConnections = useRef<Map<number, WebSocket>>(new Map())

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 5000) // Refresh every 5 seconds
    return () => {
      clearInterval(interval)
      // Close all WebSocket connections
      wsConnections.current.forEach((ws) => ws.close())
      wsConnections.current.clear()
    }
  }, [])

  const loadJobs = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await batchReprocessingService.listJobs()
      setJobs(data)

      // Set up WebSocket connections for running jobs
      data.forEach((job) => {
        if (job.status === 'running' && !wsConnections.current.has(job.id)) {
          setupWebSocket(job.id)
        }
      })
    } catch (err: any) {
      setError(err.message || 'Failed to load batch jobs')
    } finally {
      setLoading(false)
    }
  }

  const setupWebSocket = (jobId: number) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/batch-job/${jobId}`
    
    try {
      const ws = new WebSocket(wsUrl)
      
      ws.onmessage = (event) => {
        const update = JSON.parse(event.data)
        setJobs((prevJobs) =>
          prevJobs.map((job) => (job.id === update.job_id ? { ...job, ...update } : job))
        )
      }

      ws.onerror = (error) => {
        console.error(`WebSocket error for job ${jobId}:`, error)
      }

      ws.onclose = () => {
        wsConnections.current.delete(jobId)
      }

      wsConnections.current.set(jobId, ws)
    } catch (err) {
      console.error(`Failed to setup WebSocket for job ${jobId}:`, err)
    }
  }

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)

    try {
      const request: BatchJobCreateRequest = {
        job_name: jobName,
        property_ids: propertyIds
          ? propertyIds.split(',').map((id) => parseInt(id.trim())).filter((id) => !isNaN(id))
          : undefined,
        date_range_start: dateStart || undefined,
        date_range_end: dateEnd || undefined,
        document_types: documentTypes
          ? documentTypes.split(',').map((type) => type.trim()).filter((type) => type.length > 0)
          : undefined,
      }

      const job = await batchReprocessingService.createJob(request)
      const startedJob = await batchReprocessingService.startJob(job.id)

      setJobs((prev) => [startedJob, ...prev])
      setShowCreateForm(false)
      resetForm()

      // Set up WebSocket for the new job
      if (startedJob.status === 'running') {
        setupWebSocket(startedJob.id)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create batch job')
    } finally {
      setCreating(false)
    }
  }

  const handleCancelJob = async (jobId: number) => {
    if (!confirm('Are you sure you want to cancel this job?')) return

    try {
      await batchReprocessingService.cancelJob(jobId)
      await loadJobs()
    } catch (err: any) {
      setError(err.message || 'Failed to cancel job')
    }
  }

  const resetForm = () => {
    setJobName('')
    setPropertyIds('')
    setDateStart('')
    setDateEnd('')
    setDocumentTypes('')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'running':
        return <Loader className="h-5 w-5 text-blue-500 animate-spin" />
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />
      case 'cancelled':
        return <X className="h-5 w-5 text-gray-500" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900">Batch Reprocessing</h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all flex items-center gap-2"
        >
          <Play size={18} />
          Create New Job
        </button>
      </div>

      {/* Create Job Form */}
      {showCreateForm && (
        <form onSubmit={handleCreateJob} className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Job Name *
              </label>
              <input
                type="text"
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Reprocess Q4 2024 Documents"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Property IDs (comma-separated)
              </label>
              <input
                type="text"
                value={propertyIds}
                onChange={(e) => setPropertyIds(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., 1, 2, 3"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Types (comma-separated)
              </label>
              <input
                type="text"
                value={documentTypes}
                onChange={(e) => setDocumentTypes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., income_statement, balance_sheet"
              />
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex gap-3 mt-4">
            <button
              type="submit"
              disabled={creating}
              className={`
                px-4 py-2 rounded-lg font-medium transition-all
                ${creating
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
                }
              `}
            >
              {creating ? 'Creating...' : 'Create & Start Job'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false)
                resetForm()
                setError(null)
              }}
              className="px-4 py-2 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Jobs List */}
      {loading && jobs.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading jobs...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-8">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No batch reprocessing jobs found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    {getStatusIcon(job.status)}
                    <h4 className="font-semibold text-gray-900">{job.job_name}</h4>
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(job.status)}`}>
                      {job.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">Total:</span> {job.total_documents}
                    </div>
                    <div>
                      <span className="font-medium">Processed:</span> {job.processed_documents}
                    </div>
                    <div>
                      <span className="font-medium">Success:</span>{' '}
                      <span className="text-green-600">{job.successful_count}</span>
                    </div>
                    <div>
                      <span className="font-medium">Skipped:</span>{' '}
                      <span className="text-yellow-600">{job.skipped_count || 0}</span>
                    </div>
                    <div>
                      <span className="font-medium">Failed:</span>{' '}
                      <span className="text-red-600">{job.failed_count}</span>
                    </div>
                  </div>
                </div>
                {job.status === 'running' && (
                  <button
                    onClick={() => handleCancelJob(job.id)}
                    className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-all flex items-center gap-1"
                  >
                    <X size={14} />
                    Cancel
                  </button>
                )}
              </div>

              {/* Progress Bar */}
              {job.status === 'running' && (
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-600">Progress</span>
                    <span className="text-xs font-medium text-gray-900">{job.progress_pct}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${job.progress_pct}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Details */}
              {job.status === 'completed' && job.results_summary?.error_details && job.results_summary.error_details.length > 0 && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-yellow-600" />
                    <span className="text-sm font-medium text-yellow-800">
                      Error Details ({job.results_summary.error_details.length} items)
                    </span>
                  </div>
                  <details className="text-xs">
                    <summary className="cursor-pointer text-yellow-700 hover:text-yellow-800 mb-2">
                      View error details
                    </summary>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {job.results_summary.error_details.slice(0, 20).map((error: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white rounded border border-yellow-200">
                          <div className="font-medium text-gray-900">
                            Document {error.document_id}: {error.file_name || 'Unknown'}
                          </div>
                          <div className="text-gray-600 mt-1">
                            <span className={`px-1.5 py-0.5 rounded text-xs ${
                              error.type === 'validation' 
                                ? 'bg-yellow-100 text-yellow-800' 
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {error.type === 'validation' ? 'Skipped' : 'Failed'}
                            </span>
                            <span className="ml-2">{error.reason}</span>
                          </div>
                        </div>
                      ))}
                      {job.results_summary.error_details.length > 20 && (
                        <div className="text-yellow-700 text-xs italic">
                          ... and {job.results_summary.error_details.length - 20} more errors
                        </div>
                      )}
                    </div>
                  </details>
                </div>
              )}

              {/* Error Summary */}
              {job.status === 'completed' && job.results_summary?.error_summary && (
                <div className="mt-2 text-xs text-gray-600">
                  <span className="font-medium">Error Breakdown:</span>{' '}
                  {job.results_summary.error_summary.validation_errors || 0} validation errors,{' '}
                  {job.results_summary.error_summary.processing_errors || 0} processing errors
                </div>
              )}

              {/* Job Metadata */}
              <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-4">
                  {job.started_at && (
                    <span>Started: {new Date(job.started_at).toLocaleString()}</span>
                  )}
                  {job.estimated_completion_at && job.status === 'running' && (
                    <span>
                      ETA: {new Date(job.estimated_completion_at).toLocaleString()}
                    </span>
                  )}
                  {job.completed_at && (
                    <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>
                  )}
                </div>
                <button
                  onClick={loadJobs}
                  className="text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  <RefreshCw size={12} />
                  Refresh
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

