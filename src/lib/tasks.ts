/**
 * Task Service
 *
 * API calls for task management and monitoring
 */

import type { TaskDashboard, TaskStatus, Task } from '../types/tasks'

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1'

export class TaskService {
  /**
   * Get comprehensive task dashboard data
   */
  async getTaskDashboard(): Promise<TaskDashboard> {
    const response = await fetch(`${API_BASE_URL}/tasks/dashboard`, {
      credentials: 'include'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch task dashboard: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Get status of a specific task
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      credentials: 'include'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch task status: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Cancel a running task
   */
  async cancelTask(taskId: string): Promise<{ task_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: 'DELETE',
      credentials: 'include'
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `Failed to cancel task: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Retry all failed extractions
   */
  async retryFailedExtractions(): Promise<{ message: string; queued_count: number; total_failed: number }> {
    const response = await fetch(`${API_BASE_URL}/documents/uploads/reprocess-failed`, {
      method: 'POST',
      credentials: 'include'
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `Failed to retry extractions: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Trigger recovery of stuck documents
   */
  async recoverStuckDocuments(): Promise<{ recovered: number; errors: number; total_found: number }> {
    // This would trigger the recover_stuck_extractions task
    // For now, we'll use the existing reprocess endpoint as a proxy
    // In the future, we could add a dedicated endpoint
    const response = await fetch(`${API_BASE_URL}/documents/uploads/reprocess-failed`, {
      method: 'POST',
      credentials: 'include'
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `Failed to recover stuck documents: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Get extended task history (last 7 days)
   */
  async getTaskHistory(days: number = 7): Promise<Task[]> {
    const response = await fetch(`${API_BASE_URL}/tasks/history?days=${days}`, {
      credentials: 'include'
    })
    
    if (!response.ok) {
      // If endpoint doesn't exist yet, return empty array
      if (response.status === 404) {
        return []
      }
      throw new Error(`Failed to fetch task history: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Bulk cancel tasks
   */
  async bulkCancelTasks(taskIds: string[]): Promise<{ cancelled: number; failed: number }> {
    const response = await fetch(`${API_BASE_URL}/tasks/bulk/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_ids: taskIds }),
      credentials: 'include'
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `Failed to cancel tasks: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  /**
   * Export task history to CSV
   */
  exportTasksToCSV(tasks: Task[]): string {
    const headers = ['Task ID', 'Type', 'Status', 'Document', 'Property', 'Duration (s)', 'Completed At']
    const rows = tasks.map(task => [
      task.task_id,
      task.task_type,
      task.status,
      task.document_name || 'N/A',
      task.property_code || 'N/A',
      task.duration_seconds?.toString() || 'N/A',
      task.completed_at || 'N/A'
    ])
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')
    
    return csvContent
  }
}

// Export singleton
export const taskService = new TaskService()

