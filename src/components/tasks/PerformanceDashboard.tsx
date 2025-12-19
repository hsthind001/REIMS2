/**
 * PerformanceDashboard Component
 * 
 * Phase 3: Performance dashboards showing worker utilization,
 * queue depth over time, and task type performance comparison
 */

import { Card } from '../design-system'
import { TrendingUp, Activity, AlertCircle } from 'lucide-react'
import type { TaskDashboard, Worker } from '../../types/tasks'

interface PerformanceDashboardProps {
  dashboard: TaskDashboard
  historicalData?: Array<{
    timestamp: string;
    queue_depth: number;
    workers_active: number;
    tasks_completed: number;
  }>
}

export function PerformanceDashboard({ dashboard, historicalData = [] }: PerformanceDashboardProps) {
  // Calculate worker utilization
  const workerUtilization = dashboard.workers.length > 0
    ? dashboard.workers.reduce((sum, w) => sum + w.active_tasks, 0) / dashboard.workers.length
    : 0;

  // Calculate average queue depth (if historical data available)
  const avgQueueDepth = historicalData.length > 0
    ? historicalData.reduce((sum, d) => sum + d.queue_depth, 0) / historicalData.length
    : dashboard.queue_stats.pending + dashboard.queue_stats.processing;

  // Predict queue depth trend
  const queueTrend = historicalData.length >= 2
    ? historicalData[historicalData.length - 1].queue_depth - historicalData[0].queue_depth
    : 0;

  // Calculate task throughput (tasks per hour)
  const tasksPerHour = dashboard.queue_stats.completed_today > 0
    ? Math.round((dashboard.queue_stats.completed_today / 24) * 60) // Approximate
    : 0;

  // Performance alerts
  const alerts: Array<{ type: 'warning' | 'danger' | 'info'; message: string }> = [];
  
  if (queueTrend > 5) {
    alerts.push({
      type: 'warning',
      message: `Queue depth is increasing (+${queueTrend} tasks). Consider scaling workers.`
    });
  }
  
  if (dashboard.queue_stats.pending > 50) {
    alerts.push({
      type: 'danger',
      message: `High queue depth: ${dashboard.queue_stats.pending} pending tasks. System may be overloaded.`
    });
  }
  
  if (dashboard.queue_stats.success_rate < 90) {
    alerts.push({
      type: 'warning',
      message: `Success rate is below 90% (${dashboard.queue_stats.success_rate.toFixed(1)}%). Review failed tasks.`
    });
  }
  
  if (workerUtilization > 10) {
    alerts.push({
      type: 'info',
      message: `High worker utilization: ${workerUtilization.toFixed(1)} tasks per worker on average.`
    });
  }

  return (
    <div className="space-y-6">
      {/* Performance Alerts */}
      {alerts.length > 0 && (
        <Card className="p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-warning" />
            Performance Alerts
          </h3>
          <div className="space-y-2">
            {alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`p-3 rounded ${
                  alert.type === 'danger' ? 'bg-danger-light text-danger' :
                  alert.type === 'warning' ? 'bg-warning-light text-warning' :
                  'bg-info-light text-info'
                }`}
              >
                {alert.message}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Key Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-5 h-5 text-info" />
            <div className="text-sm text-text-secondary">Worker Utilization</div>
          </div>
          <div className="text-2xl font-bold">{workerUtilization.toFixed(1)}</div>
          <div className="text-xs text-text-secondary mt-1">tasks/worker avg</div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-success" />
            <div className="text-sm text-text-secondary">Queue Depth</div>
          </div>
          <div className="text-2xl font-bold">{avgQueueDepth.toFixed(0)}</div>
          <div className="text-xs text-text-secondary mt-1">
            {queueTrend > 0 ? `+${queueTrend} trend` : queueTrend < 0 ? `${queueTrend} trend` : 'stable'}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-5 h-5 text-primary" />
            <div className="text-sm text-text-secondary">Throughput</div>
          </div>
          <div className="text-2xl font-bold">{tasksPerHour}</div>
          <div className="text-xs text-text-secondary mt-1">tasks/hour</div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-success" />
            <div className="text-sm text-text-secondary">Success Rate</div>
          </div>
          <div className="text-2xl font-bold">{dashboard.queue_stats.success_rate.toFixed(1)}%</div>
          <div className="text-xs text-text-secondary mt-1">today</div>
        </Card>
      </div>

      {/* Worker Performance Comparison */}
      {dashboard.workers.length > 1 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Worker Performance</h3>
          <div className="space-y-3">
            {dashboard.workers.map((worker) => (
              <div key={worker.worker_id} className="flex items-center justify-between p-3 bg-surface-secondary rounded">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${
                    worker.status === 'online' ? 'bg-success' : 'bg-danger'
                  }`} />
                  <div>
                    <div className="font-medium">{worker.worker_id}</div>
                    <div className="text-sm text-text-secondary">
                      {worker.active_tasks} active task(s)
                    </div>
                  </div>
                </div>
                <div className="text-sm text-text-secondary">
                  {worker.cpu_percent > 0 && `${worker.cpu_percent.toFixed(1)}% CPU`}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

