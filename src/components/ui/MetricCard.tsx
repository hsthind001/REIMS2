import React from 'react';
import { Card } from './Card';
import { Skeleton } from './Skeleton';
import './metric-card.css';

type Trend = 'up' | 'down' | 'neutral';

export interface MetricCardProps {
  title: string;
  value: string | number;
  delta?: number;
  trend?: Trend;
  comparison?: string;
  target?: number;
  status?: 'success' | 'warning' | 'danger' | 'info';
  loading?: boolean;
  sparklineData?: number[];
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
  sparklineData,
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

  // Calculate sparkline path
  const renderSparkline = () => {
    if (!sparklineData || sparklineData.length < 2) return null;

    const width = 120;
    const height = 40;
    const min = Math.min(...sparklineData);
    const max = Math.max(...sparklineData);
    const range = max - min || 1;

    const points = sparklineData.map((d, i) => {
      const x = (i / (sparklineData.length - 1)) * width;
      const y = height - ((d - min) / range) * height;
      return `${x},${y}`;
    }).join(' ');

    const trendColor = trend === 'up' ? 'var(--color-success)' : trend === 'down' ? 'var(--color-danger)' : 'var(--color-text-secondary)';

    return (
      <div className="ui-metric-sparkline">
        <svg width="100%" height="40" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          <path
            d={`M ${points}`}
            fill="none"
            stroke={trendColor}
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
          <path
            d={`M 0,${height} L ${points} L ${width},${height} Z`}
            fill={trendColor}
            fillOpacity="0.1"
          />
        </svg>
      </div>
    );
  };

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
      <div className="ui-metric-content-wrapper" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div className="ui-metric-value">{value}</div>
          {delta !== undefined && (
            <div className={`ui-metric-delta ui-trend-${trend}`}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '•'} {delta}%
            </div>
          )}
          {comparison && <div className="ui-metric-comparison">{comparison}</div>}
        </div>
        {sparklineData && renderSparkline()}
      </div>
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
