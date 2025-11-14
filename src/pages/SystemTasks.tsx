import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface Task {
  id: string;
  task_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  eta_seconds?: number;
  started_at?: string;
  completed_at?: string;
  worker_id?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  next_retry_at?: string;
  metadata?: {
    property_name?: string;
    document_name?: string;
    record_count?: number;
  };
}

interface TaskStats {
  task_type: string;
  total: number;
  success: number;
  failed: number;
  avg_time_seconds: number;
}

interface Worker {
  worker_id: string;
  status: 'online' | 'offline';
  active_tasks: number;
  memory_mb: number;
  cpu_percent: number;
}

export default function SystemTasks() {
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const [queuedTasks, setQueuedTasks] = useState<Task[]>([]);
  const [failedTasks, setFailedTasks] = useState<Task[]>([]);
  const [taskStats, setTaskStats] = useState<TaskStats[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadTasks();

    if (autoRefresh) {
      const interval = setInterval(loadTasks, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadTasks = async () => {
    try {
      setError('');

      const [tasksRes, statsRes, workersRes] = await Promise.all([
        fetch(`${API_BASE_URL}/tasks`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/tasks/stats`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/tasks/workers`, { credentials: 'include' })
      ]);

      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        setActiveTasks(tasksData.active || []);
        setQueuedTasks(tasksData.queued || []);
        setFailedTasks(tasksData.failed || []);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setTaskStats(statsData.stats || []);
      }

      if (workersRes.ok) {
        const workersData = await workersRes.json();
        setWorkers(workersData.workers || []);
      }
    } catch (err) {
      console.error('Failed to load tasks:', err);
      setError('Failed to load task data');
    } finally {
      setLoading(false);
    }
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/retry`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to retry task');

      loadTasks();
    } catch (err) {
      console.error('Failed to retry task:', err);
      setError('Failed to retry task');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to cancel this task?')) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to cancel task');

      loadTasks();
    } catch (err) {
      console.error('Failed to cancel task:', err);
      setError('Failed to cancel task');
    }
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const formatETA = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    return formatDuration(seconds);
  };

  const getTaskTypeIcon = (taskType: string) => {
    if (taskType.includes('PDF') || taskType.includes('extraction')) return '📄';
    if (taskType.includes('import')) return '📥';
    if (taskType.includes('summary')) return '📝';
    if (taskType.includes('research')) return '🔍';
    if (taskType.includes('report')) return '📊';
    if (taskType.includes('variance')) return '📈';
    return '⚙️';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'var(--success-color)';
      case 'processing': return 'var(--primary-color)';
      case 'pending': return 'var(--warning-color)';
      case 'failed': return 'var(--error-color)';
      default: return 'var(--secondary-color)';
    }
  };

  const totalStats = taskStats.reduce((acc, stat) => ({
    total: acc.total + stat.total,
    success: acc.success + stat.success,
    failed: acc.failed + stat.failed
  }), { total: 0, success: 0, failed: 0 });

  const successRate = totalStats.total > 0
    ? ((totalStats.success / totalStats.total) * 100).toFixed(1)
    : '0.0';

  if (loading && activeTasks.length === 0) {
    return (
      <div className="page">
        <div className="loading">Loading tasks...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Background Tasks Monitoring</h1>
            <p className="page-subtitle">Monitor Celery workers, task queues, and job execution</p>
          </div>
          <div>
            <label style={{ marginRight: '1rem' }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              {' '}Auto-refresh (5s)
            </label>
            <button className="btn btn-secondary" onClick={loadTasks}>
              🔄 Refresh Now
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="page-content">
        {/* Active Tasks */}
        <div className="card">
          <h3>Active Tasks ({activeTasks.length} running)</h3>
          {activeTasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
              No active tasks at the moment
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '1rem' }}>
              {activeTasks.map(task => (
                <div
                  key={task.id}
                  style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>
                        {getTaskTypeIcon(task.task_type)} {task.task_type}
                        {task.metadata?.property_name && `: ${task.metadata.property_name}`}
                        {task.metadata?.document_name && ` - ${task.metadata.document_name}`}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                        Status: <span style={{ color: getStatusColor(task.status) }}>{task.status}</span> |
                        Progress: {task.progress}% |
                        ETA: {formatETA(task.eta_seconds)} |
                        Started: {task.started_at ? new Date(task.started_at).toLocaleTimeString() : 'N/A'} |
                        Worker: {task.worker_id || 'N/A'}
                      </div>
                      <div style={{ background: 'var(--background-light)', borderRadius: '0.25rem', height: '0.5rem', overflow: 'hidden' }}>
                        <div
                          style={{
                            background: 'var(--primary-color)',
                            width: `${task.progress}%`,
                            height: '100%',
                            transition: 'width 0.3s ease'
                          }}
                        />
                      </div>
                    </div>
                    <div style={{ marginLeft: '1rem' }}>
                      <button className="btn btn-secondary" style={{ marginRight: '0.5rem' }}>
                        View Logs
                      </button>
                      <button
                        className="btn"
                        style={{ background: 'var(--error-color)', color: 'white' }}
                        onClick={() => handleCancelTask(task.id)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Queued Tasks */}
        <div className="card">
          <h3>Queued Tasks ({queuedTasks.length} pending)</h3>
          {queuedTasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-secondary)' }}>
              No tasks in queue
            </div>
          ) : (
            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
              {queuedTasks.slice(0, 10).map(task => (
                <li key={task.id} style={{ marginBottom: '0.5rem' }}>
                  {getTaskTypeIcon(task.task_type)} {task.task_type}
                  {task.metadata?.record_count && ` (${task.metadata.record_count} records)`}
                </li>
              ))}
              {queuedTasks.length > 10 && (
                <li style={{ color: 'var(--text-secondary)' }}>
                  ... and {queuedTasks.length - 10} more
                </li>
              )}
            </ul>
          )}
        </div>

        {/* Task History */}
        <div className="card">
          <h3>Task History (Last 24 Hours)</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Task Type</th>
                  <th>Total</th>
                  <th>Success</th>
                  <th>Failed</th>
                  <th>Avg Time</th>
                </tr>
              </thead>
              <tbody>
                {taskStats.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                      No task history available
                    </td>
                  </tr>
                ) : (
                  taskStats.map((stat, idx) => (
                    <tr key={idx}>
                      <td>
                        {getTaskTypeIcon(stat.task_type)} <strong>{stat.task_type}</strong>
                      </td>
                      <td>{stat.total}</td>
                      <td style={{ color: 'var(--success-color)' }}>{stat.success}</td>
                      <td style={{ color: stat.failed > 0 ? 'var(--error-color)' : 'inherit' }}>{stat.failed}</td>
                      <td>{formatDuration(stat.avg_time_seconds)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '1rem', padding: '0.5rem', background: 'var(--background-light)', borderRadius: '0.25rem' }}>
            <strong>Success Rate:</strong>{' '}
            <span style={{ color: Number(successRate) >= 95 ? 'var(--success-color)' : 'var(--warning-color)' }}>
              {successRate}% {Number(successRate) >= 95 ? '✅' : '⚠️'}
            </span>
          </div>
        </div>

        {/* Failed Tasks */}
        {failedTasks.length > 0 && (
          <div className="card">
            <h3>Failed Tasks ({failedTasks.length} in last 24h)</h3>
            <div style={{ display: 'grid', gap: '1rem' }}>
              {failedTasks.map(task => (
                <div
                  key={task.id}
                  style={{
                    border: '1px solid var(--error-color)',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    background: '#fff5f5',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '0.25rem', color: 'var(--error-color)' }}>
                        ❌ {task.task_type}
                        {task.metadata?.document_name && `: ${task.metadata.document_name}`}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                        Failed: {task.completed_at ? new Date(task.completed_at).toLocaleString() : 'N/A'} |
                        Retries: {task.retry_count}/{task.max_retries}
                        {task.next_retry_at && ` | Next retry: ${new Date(task.next_retry_at).toLocaleTimeString()}`}
                      </div>
                      <div style={{ padding: '0.5rem', background: 'white', borderRadius: '0.25rem', fontSize: '0.9rem', fontFamily: 'monospace' }}>
                        <strong>Error:</strong> {task.error_message || 'Unknown error'}
                      </div>
                      {task.retry_count >= task.max_retries && (
                        <div style={{ marginTop: '0.5rem', color: 'var(--error-color)', fontWeight: 'bold' }}>
                          ⚠️ Manual intervention needed - Max retries exceeded
                        </div>
                      )}
                    </div>
                    <div style={{ marginLeft: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <button className="btn btn-primary" onClick={() => handleRetryTask(task.id)}>
                        Retry Now
                      </button>
                      <button className="btn btn-secondary">View Error Log</button>
                      <button className="btn btn-secondary" onClick={() => handleCancelTask(task.id)}>
                        Skip
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Worker Status */}
        <div className="card">
          <h3>Worker Status</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Worker</th>
                  <th>Status</th>
                  <th>Active Tasks</th>
                  <th>Memory (MB)</th>
                  <th>CPU %</th>
                </tr>
              </thead>
              <tbody>
                {workers.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                      No workers available
                    </td>
                  </tr>
                ) : (
                  workers.map((worker, idx) => (
                    <tr key={idx}>
                      <td><code>{worker.worker_id}</code></td>
                      <td>
                        <span style={{ color: worker.status === 'online' ? 'var(--success-color)' : 'var(--error-color)' }}>
                          {worker.status === 'online' ? '🟢 UP' : '🔴 DOWN'}
                        </span>
                      </td>
                      <td>{worker.active_tasks} tasks</td>
                      <td>{worker.memory_mb.toFixed(1)} MB</td>
                      <td>{worker.cpu_percent}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Actions */}
        <div className="card">
          <h3>Actions</h3>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary">Export Task Log</button>
            <button className="btn btn-secondary">Clear Completed Tasks</button>
            <button className="btn btn-secondary">Purge Failed Tasks</button>
            <button className="btn btn-secondary">Restart All Workers</button>
          </div>
        </div>
      </div>
    </div>
  );
}
