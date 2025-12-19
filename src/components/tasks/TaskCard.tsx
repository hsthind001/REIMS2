/**
 * TaskCard Component
 * 
 * Displays an individual active task with progress and actions
 */

import { ProgressBar } from '../design-system'
import { Button } from '../design-system'
import { Play, Pause, X, Eye } from 'lucide-react'
import type { Task } from '../../types/tasks'

interface TaskCardProps {
  task: Task
  onViewDetails: (task: Task) => void
  onCancel: (taskId: string) => void
  canceling?: boolean
}

export function TaskCard({ task, onViewDetails, onCancel, canceling = false }: TaskCardProps) {
  const getTaskTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'document_extraction': 'Document Extraction',
      'anomaly_detection': 'Anomaly Detection',
      'recovery': 'Recovery',
      'email': 'Email',
      'batch_processing': 'Batch Processing',
      'other': 'Other'
    }
    return labels[type] || type
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PROCESSING':
        return 'info'
      case 'SUCCESS':
        return 'success'
      case 'FAILURE':
        return 'danger'
      case 'PENDING':
        return 'warning'
      default:
        return 'default'
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  const formatETA = (etaSeconds?: number) => {
    if (!etaSeconds) return 'Calculating...'
    if (etaSeconds < 60) return `${etaSeconds}s`
    const mins = Math.floor(etaSeconds / 60)
    return `${mins}m`
  }

  return (
    <div className="bg-surface rounded-lg border border-border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              getStatusColor(task.status) === 'info' ? 'bg-info-light text-info' :
              getStatusColor(task.status) === 'success' ? 'bg-success-light text-success' :
              getStatusColor(task.status) === 'danger' ? 'bg-danger-light text-danger' :
              'bg-warning-light text-warning'
            }`}>
              {task.status}
            </span>
            <span className="text-sm text-text-secondary">{getTaskTypeLabel(task.task_type)}</span>
          </div>
          <h4 className="font-semibold text-text-primary">
            {task.document_name || task.task_name}
          </h4>
          {task.property_code && (
            <p className="text-sm text-text-secondary">Property: {task.property_code}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="info"
            size="sm"
            icon={<Eye className="w-4 h-4" />}
            onClick={() => onViewDetails(task)}
          >
            Details
          </Button>
          {task.status === 'PROCESSING' && (
            <Button
              variant="danger"
              size="sm"
              icon={<X className="w-4 h-4" />}
              onClick={() => onCancel(task.task_id)}
              disabled={canceling}
            >
              {canceling ? 'Canceling...' : 'Cancel'}
            </Button>
          )}
        </div>
      </div>

      {task.status === 'PROCESSING' && (
        <div className="mb-3">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-text-secondary">Progress</span>
            <span className="font-medium">{task.progress}%</span>
          </div>
          <ProgressBar
            value={task.progress}
            max={100}
            variant={getStatusColor(task.status) as any}
            height="sm"
          />
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        {task.current_step && (
          <div>
            <div className="text-text-secondary">Status</div>
            <div className="font-medium truncate" title={task.current_step}>
              {task.current_step}
            </div>
          </div>
        )}
        {task.started_at && (
          <div>
            <div className="text-text-secondary">Started</div>
            <div className="font-medium">
              {new Date(task.started_at).toLocaleTimeString()}
            </div>
          </div>
        )}
        {task.eta_seconds && task.status === 'PROCESSING' && (
          <div>
            <div className="text-text-secondary">ETA</div>
            <div className="font-medium">{formatETA(task.eta_seconds)}</div>
          </div>
        )}
        {task.duration_seconds && (
          <div>
            <div className="text-text-secondary">Duration</div>
            <div className="font-medium">{formatDuration(task.duration_seconds)}</div>
          </div>
        )}
      </div>
    </div>
  )
}

