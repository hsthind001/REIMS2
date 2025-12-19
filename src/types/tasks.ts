/**
 * TypeScript types for task management
 */

export interface Task {
  task_id: string;
  task_name: string;
  task_type: 'document_extraction' | 'anomaly_detection' | 'recovery' | 'email' | 'batch_processing' | 'other';
  status: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILURE' | 'REVOKED';
  progress: number;
  current_step?: string;
  upload_id?: number;
  document_name?: string;
  property_code?: string;
  started_at?: string;
  eta_seconds?: number;
  worker_id?: string;
  duration_seconds?: number;
  completed_at?: string;
  error?: string;
}

export interface QueueStats {
  pending: number;
  processing: number;
  completed_today: number;
  failed_today: number;
  success_rate: number;
}

export interface Worker {
  worker_id: string;
  status: 'online' | 'offline';
  active_tasks: number;
  cpu_percent: number;
  memory_mb: number;
}

export interface TaskStatistics {
  avg_extraction_time: number;
  total_tasks_today: number;
  by_type: Record<string, {
    count: number;
    avg_time: number;
  }>;
}

export interface TaskDashboard {
  active_tasks: Task[];
  queue_stats: QueueStats;
  workers: Worker[];
  recent_tasks: Task[];
  task_statistics: TaskStatistics;
  error?: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  ready: boolean;
  successful?: boolean;
  result?: any;
  error?: string;
  progress?: {
    upload_id?: number;
    status?: string;
    progress?: number;
  };
}

