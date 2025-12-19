/**
 * WorkerStatus Component
 * 
 * Displays Celery worker health and status
 */

import { Card } from '../design-system'
import { CheckCircle, XCircle, Activity } from 'lucide-react'
import type { Worker } from '../../types/tasks'

interface WorkerStatusProps {
  workers: Worker[]
}

export function WorkerStatus({ workers }: WorkerStatusProps) {
  if (workers.length === 0) {
    return (
      <Card className="p-4">
        <div className="flex items-center gap-2 text-warning">
          <XCircle className="w-5 h-5" />
          <span className="font-semibold">No workers available</span>
        </div>
        <p className="text-sm text-text-secondary mt-2">
          Celery workers may be offline. Check worker status.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {workers.map((worker) => (
        <Card key={worker.worker_id} className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {worker.status === 'online' ? (
                <CheckCircle className="w-5 h-5 text-success" />
              ) : (
                <XCircle className="w-5 h-5 text-danger" />
              )}
              <div>
                <div className="font-semibold text-text-primary">{worker.worker_id}</div>
                <div className="text-sm text-text-secondary">
                  {worker.status === 'online' ? 'Online' : 'Offline'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="text-center">
                <div className="text-text-secondary">Active Tasks</div>
                <div className="font-bold text-lg">{worker.active_tasks}</div>
              </div>
              {worker.cpu_percent > 0 && (
                <div className="text-center">
                  <div className="text-text-secondary">CPU</div>
                  <div className="font-medium">{worker.cpu_percent.toFixed(1)}%</div>
                </div>
              )}
              {worker.memory_mb > 0 && (
                <div className="text-center">
                  <div className="text-text-secondary">Memory</div>
                  <div className="font-medium">{worker.memory_mb} MB</div>
                </div>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}

