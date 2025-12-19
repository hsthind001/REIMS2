/**
 * TaskScheduler Component
 * 
 * Phase 3: Task scheduling interface for scheduling tasks
 * for future execution and recurring schedules
 */

import { useState } from 'react'
import { Card, Button } from '../design-system'
import { Calendar, Clock, Repeat, Plus, X } from 'lucide-react'

interface ScheduledTask {
  id: string;
  task_type: string;
  schedule_type: 'once' | 'recurring';
  scheduled_time: string;
  cron_expression?: string;
  parameters: Record<string, any>;
}

interface TaskSchedulerProps {
  onSchedule: (task: ScheduledTask) => Promise<void>
}

export function TaskScheduler({ onSchedule }: TaskSchedulerProps) {
  const [showScheduler, setShowScheduler] = useState(false);
  const [scheduleType, setScheduleType] = useState<'once' | 'recurring'>('once');
  const [scheduledTime, setScheduledTime] = useState('');
  const [cronExpression, setCronExpression] = useState('');
  const [taskType, setTaskType] = useState('extract_document');
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);

  const handleSchedule = async () => {
    if (!scheduledTime && scheduleType === 'once') {
      alert('Please select a scheduled time');
      return;
    }
    if (!cronExpression && scheduleType === 'recurring') {
      alert('Please provide a cron expression');
      return;
    }

    const newTask: ScheduledTask = {
      id: `scheduled_${Date.now()}`,
      task_type: taskType,
      schedule_type: scheduleType,
      scheduled_time: scheduledTime,
      cron_expression: scheduleType === 'recurring' ? cronExpression : undefined,
      parameters: {}
    };

    try {
      await onSchedule(newTask);
      setScheduledTasks([...scheduledTasks, newTask]);
      setScheduledTime('');
      setCronExpression('');
      setShowScheduler(false);
      alert('Task scheduled successfully');
    } catch (error: any) {
      alert(`Failed to schedule task: ${error.message || 'Unknown error'}`);
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Calendar className="w-5 h-5" />
          Task Scheduler
        </h3>
        <Button
          variant="primary"
          size="sm"
          icon={<Plus className="w-4 h-4" />}
          onClick={() => setShowScheduler(!showScheduler)}
        >
          {showScheduler ? 'Cancel' : 'Schedule Task'}
        </Button>
      </div>

      {showScheduler && (
        <div className="p-4 bg-surface-secondary rounded space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Task Type</label>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded bg-surface"
            >
              <option value="extract_document">Document Extraction</option>
              <option value="anomaly_detection">Anomaly Detection</option>
              <option value="recover_stuck_extractions">Recover Stuck Extractions</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Schedule Type</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="once"
                  checked={scheduleType === 'once'}
                  onChange={(e) => setScheduleType(e.target.value as 'once' | 'recurring')}
                />
                <Clock className="w-4 h-4" />
                <span>Once</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="recurring"
                  checked={scheduleType === 'recurring'}
                  onChange={(e) => setScheduleType(e.target.value as 'once' | 'recurring')}
                />
                <Repeat className="w-4 h-4" />
                <span>Recurring</span>
              </label>
            </div>
          </div>

          {scheduleType === 'once' ? (
            <div>
              <label className="block text-sm font-medium mb-1">Scheduled Time</label>
              <input
                type="datetime-local"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded bg-surface"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium mb-1">Cron Expression</label>
              <input
                type="text"
                placeholder="0 2 * * * (Daily at 2 AM)"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded bg-surface"
              />
              <div className="text-xs text-text-secondary mt-1">
                Format: minute hour day month weekday (e.g., "0 2 * * *" = Daily at 2 AM)
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="primary" onClick={handleSchedule}>
              Schedule Task
            </Button>
            <Button variant="default" onClick={() => setShowScheduler(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Scheduled Tasks List */}
      {scheduledTasks.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="font-semibold">Scheduled Tasks</h4>
          {scheduledTasks.map((task) => (
            <div key={task.id} className="p-3 bg-surface-secondary rounded flex items-center justify-between">
              <div>
                <div className="font-medium capitalize">{task.task_type.replace('_', ' ')}</div>
                <div className="text-sm text-text-secondary">
                  {task.schedule_type === 'once' 
                    ? `Scheduled for ${new Date(task.scheduled_time).toLocaleString()}`
                    : `Recurring: ${task.cron_expression}`
                  }
                </div>
              </div>
              <Button
                variant="danger"
                size="sm"
                icon={<X className="w-4 h-4" />}
                onClick={() => setScheduledTasks(scheduledTasks.filter(t => t.id !== task.id))}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

