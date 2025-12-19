/**
 * TaskDetailsModal Component
 * 
 * Shows detailed information about a specific task
 */

import { useState, useEffect } from 'react'
import { Card, Button, ProgressBar } from '../design-system'
import { X, RefreshCw, FileText, AlertCircle } from 'lucide-react'
import { taskService } from '../../lib/tasks'
import type { Task, TaskStatus } from '../../types/tasks'

interface TaskDetailsModalProps {
  task: Task
  onClose: () => void
  onRetry?: (taskId: string) => void
  onCancel?: (taskId: string) => void
}

export function TaskDetailsModal({ task, onClose, onRetry, onCancel }: TaskDetailsModalProps) {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTaskStatus()
  }, [task.task_id])

  const loadTaskStatus = async () => {
    try {
      setLoading(true)
      setError(null)
      const status = await taskService.getTaskStatus(task.task_id)
      setTaskStatus(status)
    } catch (err: any) {
      setError(err.message || 'Failed to load task details')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!onCancel) return
    try {
      await taskService.cancelTask(task.task_id)
      onCancel(task.task_id)
      onClose()
    } catch (err: any) {
      alert(`Failed to cancel task: ${err.message}`)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'success'
      case 'FAILURE':
        return 'danger'
      case 'PROCESSING':
      case 'PENDING':
        return 'info'
      default:
        return 'default'
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-surface rounded-xl p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Task Details</h2>
          <Button variant="default" size="sm" icon={<X className="w-4 h-4" />} onClick={onClose}>
            Close
          </Button>
        </div>

        {loading ? (
          <div className="text-center py-8">Loading task details...</div>
        ) : error ? (
          <Card variant="danger" className="p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {/* Task Overview */}
            <Card className="p-4">
              <h3 className="font-semibold mb-3">Task Information</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-text-secondary">Task ID</div>
                  <div className="font-mono text-xs">{task.task_id}</div>
                </div>
                <div>
                  <div className="text-text-secondary">Type</div>
                  <div className="font-medium">{task.task_type}</div>
                </div>
                <div>
                  <div className="text-text-secondary">Status</div>
                  <div className={`font-medium ${
                    getStatusColor(task.status) === 'success' ? 'text-success' :
                    getStatusColor(task.status) === 'danger' ? 'text-danger' :
                    'text-info'
                  }`}>
                    {task.status}
                  </div>
                </div>
                {task.worker_id && (
                  <div>
                    <div className="text-text-secondary">Worker</div>
                    <div className="font-medium">{task.worker_id}</div>
                  </div>
                )}
              </div>
            </Card>

            {/* Document Information */}
            {task.upload_id && (
              <Card className="p-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Document Information
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-text-secondary">Document</div>
                    <div className="font-medium">{task.document_name || 'N/A'}</div>
                  </div>
                  {task.property_code && (
                    <div>
                      <div className="text-text-secondary">Property</div>
                      <div className="font-medium">{task.property_code}</div>
                    </div>
                  )}
                  {task.upload_id && (
                    <div>
                      <div className="text-text-secondary">Upload ID</div>
                      <div className="font-medium">{task.upload_id}</div>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Progress */}
            {task.status === 'PROCESSING' && (
              <Card className="p-4">
                <h3 className="font-semibold mb-3">Progress</h3>
                <div className="mb-2">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-secondary">Completion</span>
                    <span className="font-medium">{task.progress}%</span>
                  </div>
                  <ProgressBar
                    value={task.progress}
                    max={100}
                    variant={getStatusColor(task.status) as any}
                    height="md"
                  />
                </div>
                {task.current_step && (
                  <div className="text-sm">
                    <div className="text-text-secondary">Current Step</div>
                    <div className="font-medium">{task.current_step}</div>
                  </div>
                )}
                {task.eta_seconds && (
                  <div className="text-sm mt-2">
                    <div className="text-text-secondary">Estimated Time Remaining</div>
                    <div className="font-medium">
                      {task.eta_seconds < 60 ? `${task.eta_seconds}s` : `${Math.floor(task.eta_seconds / 60)}m`}
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* Task Result/Error */}
            {taskStatus && (
              <>
                {taskStatus.successful && taskStatus.result && (
                  <Card variant="success" className="p-4">
                    <h3 className="font-semibold mb-2">Result</h3>
                    <pre className="text-xs bg-background p-2 rounded overflow-auto">
                      {JSON.stringify(taskStatus.result, null, 2)}
                    </pre>
                  </Card>
                )}
                {taskStatus.error && (
                  <Card variant="danger" className="p-4">
                    <h3 className="font-semibold mb-2 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      Error
                    </h3>
                    <div className="text-sm">{taskStatus.error}</div>
                  </Card>
                )}
              </>
            )}

            {/* Timing Information */}
            <Card className="p-4">
              <h3 className="font-semibold mb-3">Timing</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {task.started_at && (
                  <div>
                    <div className="text-text-secondary">Started At</div>
                    <div className="font-medium">
                      {new Date(task.started_at).toLocaleString()}
                    </div>
                  </div>
                )}
                {task.completed_at && (
                  <div>
                    <div className="text-text-secondary">Completed At</div>
                    <div className="font-medium">
                      {new Date(task.completed_at).toLocaleString()}
                    </div>
                  </div>
                )}
                {task.duration_seconds && (
                  <div>
                    <div className="text-text-secondary">Duration</div>
                    <div className="font-medium">
                      {task.duration_seconds < 60 
                        ? `${task.duration_seconds}s`
                        : `${Math.floor(task.duration_seconds / 60)}m ${task.duration_seconds % 60}s`
                      }
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Actions */}
            <div className="flex gap-2 justify-end">
              <Button variant="default" icon={<RefreshCw className="w-4 h-4" />} onClick={loadTaskStatus}>
                Refresh
              </Button>
              {task.status === 'PROCESSING' && onCancel && (
                <Button variant="danger" icon={<X className="w-4 h-4" />} onClick={handleCancel}>
                  Cancel Task
                </Button>
              )}
              {task.status === 'FAILURE' && onRetry && task.upload_id && (
                <Button variant="primary" icon={<RefreshCw className="w-4 h-4" />} onClick={() => {
                  onRetry(task.task_id)
                  onClose()
                }}>
                  Retry
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

