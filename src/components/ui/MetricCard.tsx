import React from 'react';
import { Card } from './Card';
import { Skeleton } from './Skeleton';
import './metric-card.css';

type Trend = 'up' | 'down' | 'neutral';

interface MetricCardProps {
  title: string;
  value: string | number;
  delta?: number;
  trend?: Trend;
  comparison?: string;
  target?: number;
  status?: 'success' | 'warning' | 'danger' | 'info';
  loading?: boolean;
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  delta,
  trend = 'neutral',
  comparison,
  target,
  status,
  loading = false,
  onClick,
}) => {
  if (loading) {
    return (
      <Card className="ui-metric-card">
        <Skeleton className="ui-metric-title" variant="text" />
        <Skeleton className="ui-metric-value" variant="text" />
        <Skeleton className="ui-metric-bar" />
      </Card>
    );
  }

  return (
    <Card
      className="ui-metric-card"
      hoverable
      interactive={Boolean(onClick)}
      onClick={onClick}
    >
      <div className="ui-metric-head">
        <span className="ui-metric-title">{title}</span>
        {status && <span className={`ui-metric-dot ui-status-${status}`} aria-hidden />}
      </div>
      <div className="ui-metric-value">{value}</div>
      {delta !== undefined && (
        <div className={`ui-metric-delta ui-trend-${trend}`}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '•'} {delta}%
        </div>
      )}
      {comparison && <div className="ui-metric-comparison">{comparison}</div>}
      {target !== undefined && (
        <div className="ui-metric-target">
          <div
            className="ui-metric-target-fill"
            style={{ width: `${Math.min(100, target)}%` }}
          />
        </div>
      )}
    </Card>
  );
};
