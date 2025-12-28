/**
 * Metric Card Component
 *
 * Reusable card for displaying single metrics with status and trend
 */

import { LucideIcon } from 'lucide-react';
import { Card } from '../design-system';
import TrafficLightIndicator from './TrafficLightIndicator';
import TrendIndicator from './TrendIndicator';
import type { TrafficLightStatus, TrendDirection } from '../../lib/forensic_audit';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  status?: TrafficLightStatus;
  trend?: TrendDirection;
  previousValue?: number | null;
  icon?: LucideIcon;
  iconColor?: string;
  target?: string | number;
  targetLabel?: string;
  className?: string;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  status,
  trend,
  previousValue,
  icon: Icon,
  iconColor = 'text-blue-600',
  target,
  targetLabel = 'Target',
  className = '',
}: MetricCardProps) {
  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {Icon && <Icon className={`w-5 h-5 ${iconColor}`} />}
          <h3 className="text-sm font-medium text-gray-700">{title}</h3>
        </div>
        {status && <TrafficLightIndicator status={status} size="sm" />}
      </div>

      <div className="mt-2">
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        {subtitle && (
          <div className="text-sm text-gray-500 mt-1">{subtitle}</div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {trend && (
            <TrendIndicator
              trend={trend}
              value={typeof value === 'number' ? value : undefined}
              previousValue={previousValue}
              showLabel={false}
              size="sm"
            />
          )}
          {target !== undefined && (
            <div className="text-xs text-gray-600">
              {targetLabel}: <span className="font-medium">{target}</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
