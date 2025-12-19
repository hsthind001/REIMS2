/**
 * TaskCharts Component
 * 
 * Displays task statistics charts and analytics
 */

import { Card } from '../design-system'
import { BarChart3, TrendingUp, Clock } from 'lucide-react'

interface TaskChartsProps {
  statistics: {
    avg_extraction_time: number;
    total_tasks_today: number;
    by_type: Record<string, { count: number; avg_time: number }>;
  };
  recentTasks: Array<{
    completed_at?: string;
    status: string;
    duration_seconds?: number;
  }>;
}

export function TaskCharts({ statistics, recentTasks }: TaskChartsProps) {
  // Calculate tasks over time (last 7 days)
  const getTasksOverTime = () => {
    const days = 7;
    const data: { date: string; count: number; success: number; failed: number }[] = [];
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const dayTasks = recentTasks.filter(task => {
        if (!task.completed_at) return false;
        const taskDate = new Date(task.completed_at).toISOString().split('T')[0];
        return taskDate === dateStr;
      });
      
      data.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        count: dayTasks.length,
        success: dayTasks.filter(t => t.status === 'SUCCESS').length,
        failed: dayTasks.filter(t => t.status === 'FAILURE').length
      });
    }
    
    return data;
  };

  const timeData = getTasksOverTime();
  const maxCount = Math.max(...timeData.map(d => d.count), 1);

  // Calculate success rate trend
  const getSuccessRateTrend = () => {
    const days = 7;
    const rates: number[] = [];
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const dayTasks = recentTasks.filter(task => {
        if (!task.completed_at) return false;
        const taskDate = new Date(task.completed_at).toISOString().split('T')[0];
        return taskDate === dateStr;
      });
      
      if (dayTasks.length > 0) {
        const successCount = dayTasks.filter(t => t.status === 'SUCCESS').length;
        rates.push((successCount / dayTasks.length) * 100);
      } else {
        rates.push(0);
      }
    }
    
    return rates;
  };

  const successRates = getSuccessRateTrend();
  const avgSuccessRate = successRates.reduce((a, b) => a + b, 0) / (successRates.length || 1);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Tasks Over Time Chart */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-info" />
          <h3 className="text-lg font-semibold">Tasks Over Time (Last 7 Days)</h3>
        </div>
        <div className="space-y-2">
          {timeData.map((day, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className="w-20 text-sm text-text-secondary">{day.date}</div>
              <div className="flex-1 flex items-center gap-1">
                <div className="flex-1 bg-surface-secondary rounded h-6 relative overflow-hidden">
                  <div
                    className="absolute left-0 top-0 h-full bg-success transition-all"
                    style={{ width: `${(day.success / maxCount) * 100}%` }}
                  />
                  <div
                    className="absolute left-0 top-0 h-full bg-danger transition-all"
                    style={{ 
                      left: `${(day.success / maxCount) * 100}%`,
                      width: `${(day.failed / maxCount) * 100}%` 
                    }}
                  />
                </div>
                <div className="w-12 text-right text-sm font-medium">{day.count}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-4 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-success rounded"></div>
            <span className="text-text-secondary">Success</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-danger rounded"></div>
            <span className="text-text-secondary">Failed</span>
          </div>
        </div>
      </Card>

      {/* Success Rate Trend */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-success" />
          <h3 className="text-lg font-semibold">Success Rate Trend</h3>
        </div>
        <div className="space-y-2">
          {successRates.map((rate, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className="w-20 text-sm text-text-secondary">{timeData[idx]?.date || ''}</div>
              <div className="flex-1 flex items-center gap-2">
                <div className="flex-1 bg-surface-secondary rounded h-6 relative overflow-hidden">
                  <div
                    className={`absolute left-0 top-0 h-full transition-all ${
                      rate >= 95 ? 'bg-success' : rate >= 80 ? 'bg-warning' : 'bg-danger'
                    }`}
                    style={{ width: `${rate}%` }}
                  />
                </div>
                <div className="w-16 text-right text-sm font-medium">{rate.toFixed(1)}%</div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-surface-secondary rounded">
          <div className="text-sm text-text-secondary">Average Success Rate</div>
          <div className="text-2xl font-bold">{avgSuccessRate.toFixed(1)}%</div>
        </div>
      </Card>

      {/* Average Processing Time by Type */}
      <Card className="p-6 lg:col-span-2">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-warning" />
          <h3 className="text-lg font-semibold">Average Processing Time by Type</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(statistics.by_type || {}).map(([type, stats]) => {
            const minutes = Math.floor(stats.avg_time / 60);
            const seconds = Math.floor(stats.avg_time % 60);
            
            return (
              <div key={type} className="p-4 bg-surface-secondary rounded">
                <div className="text-sm text-text-secondary mb-1 capitalize">
                  {type.replace('_', ' ')}
                </div>
                <div className="text-xl font-bold mb-1">
                  {minutes}m {seconds}s
                </div>
                <div className="text-xs text-text-secondary">
                  {stats.count} tasks
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

