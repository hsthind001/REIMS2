/**
 * TaskCard Component
 * 
 * Displays an individual active task with progress and actions
 * Now with collapse/expand functionality for better UX
 */

import { useState } from 'react'
import { ProgressBar } from '../design-system'
import { Button } from '../design-system'
import { Play, Pause, X, Eye, ChevronDown } from 'lucide-react'
import type { Task } from '../../types/tasks'

interface TaskCardProps {
  task: Task
  onViewDetails: (task: Task) => void
  onCancel: (taskId: string) => void
  canceling?: boolean
}

export function TaskCard({ task, onViewDetails, onCancel, canceling = false }: TaskCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

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
    if (etaSeconds < 60) return `~${etaSeconds}s`
    const mins = Math.floor(etaSeconds / 60)
    if (mins < 60) return `~${mins}m`
    const hours = Math.floor(mins / 60)
    const remainingMins = mins % 60
    return remainingMins > 0 ? `~${hours}h ${remainingMins}m` : `~${hours}h`
  }

  return (
    <div className="bg-surface rounded-lg border border-border hover:shadow-md transition-shadow">
      {/* Header - Always Visible */}
      <div 
        className="p-4 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
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
              {task.document_name || task.task_name || `Task ${task.task_id.substring(0, 8)}`}
            </h4>
            {task.property_code && (
              <p className="text-sm text-text-secondary">Property: {task.property_code}</p>
            )}
          </div>
          
          <div className="flex items-center gap-3 ml-4">
            {/* Progress & ETA - Always visible for processing tasks */}
            {task.status === 'PROCESSING' && (
              <div className="flex items-center gap-3">
                {task.progress !== undefined && (
                  <div className="flex items-center gap-2">
                    <div className="w-24">
                      <ProgressBar 
                        value={task.progress} 
                        max={100}
                        variant="info"
                        height="sm"
                      />
                    </div>
                    <span className="text-sm font-medium min-w-[3ch]">{task.progress}%</span>
                  </div>
                )}
                {task.eta_seconds && (
                  <div className="text-sm text-text-secondary">
                    ETA: {formatETA(task.eta_seconds)}
                  </div>
                )}
              </div>
            )}
            
            {/* Expand/Collapse Icon */}
            <ChevronDown 
              className={`w-5 h-5 text-text-secondary transition-transform duration-200 ${
                isExpanded ? 'rotate-180' : ''
              }`}
            />
          </div>
        </div>
      </div>

      {/* Expanded Details - Collapsible */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-border animate-fadeIn">
          {/* Full Progress Bar for Processing Tasks */}
          {task.status === 'PROCESSING' && task.progress !== undefined && (
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-2">
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

          {/* Task Details Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-4">
            <div>
              <div className="text-text-secondary text-xs mb-1">Task ID</div>
              <div className="font-mono text-xs truncate" title={task.task_id}>
                {task.task_id}
              </div>
            </div>
            
            {task.current_step && (
              <div>
                <div className="text-text-secondary text-xs mb-1">Current Step</div>
                <div className="font-medium truncate" title={task.current_step}>
                  {task.current_step}
                </div>
              </div>
            )}
            
            {task.started_at && (
              <div>
                <div className="text-text-secondary text-xs mb-1">Started At</div>
                <div className="font-medium">
                  {new Date(task.started_at).toLocaleString()}
                </div>
              </div>
            )}
            
            {task.duration_seconds && (
              <div>
                <div className="text-text-secondary text-xs mb-1">Duration</div>
                <div className="font-medium">{formatDuration(task.duration_seconds)}</div>
              </div>
            )}
            
            {task.eta_seconds && task.status === 'PROCESSING' && (
              <div>
                <div className="text-text-secondary text-xs mb-1">Est. Completion</div>
                <div className="font-medium">{formatETA(task.eta_seconds)}</div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button
              variant="info"
              size="sm"
              icon={<Eye className="w-4 h-4" />}
              onClick={(e) => {
                e.stopPropagation()
                onViewDetails(task)
              }}
            >
              View Details
            </Button>
            {task.status === 'PROCESSING' && (
              <Button
                variant="danger"
                size="sm"
                icon={<X className="w-4 h-4" />}
                onClick={(e) => {
                  e.stopPropagation()
                  onCancel(task.task_id)
                }}
                disabled={canceling}
              >
                {canceling ? 'Canceling...' : 'Cancel Task'}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

