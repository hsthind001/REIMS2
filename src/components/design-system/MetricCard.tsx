import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from './Card';
import { Sparkline } from './Sparkline';
import styles from './MetricCard.module.css';

export interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number; // percentage change
  trend?: 'up' | 'down' | 'neutral';
  sparkline?: number[]; // 12-month data points
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  trend,
  sparkline,
  icon,
  variant = 'default',
  className = '',
}) => {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'number') {
      if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
      if (val >= 1000) return `$${(val / 1000).toFixed(1)}K`;
      return `$${val.toFixed(0)}`;
    }
    return val;
  };

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4" />;
    if (trend === 'down') return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return styles.changeUp;
    if (trend === 'down') return styles.changeDown;
    return styles.changeNeutral;
  };

  // Get sparkline color based on variant and trend
  const getSparklineColor = () => {
    if (trend === 'up') return '#10b981'; // green-500
    if (trend === 'down') return '#ef4444'; // red-500

    switch (variant) {
      case 'success': return '#10b981';
      case 'warning': return '#f59e0b';
      case 'danger': return '#ef4444';
      case 'info': return '#0ea5e9';
      default: return '#6366f1'; // indigo-500
    }
  };

  return (
    <Card variant={variant} className={`p-6 ${className}`}>
      <div className={styles.header}>
        <div className={styles.iconContainer}>
          {icon && <span className={styles.icon}>{icon}</span>}
          <h3 className={styles.title}>{title}</h3>
        </div>
      </div>
      
      <div className="mb-2">
        <div className={styles.value}>{formatValue(value)}</div>
        {change !== undefined && (
          <div className={`${styles.change} ${getTrendColor()}`}>
            {getTrendIcon()}
            <span>{change > 0 ? '+' : ''}{change.toFixed(1)}%</span>
          </div>
        )}
      </div>

      {sparkline && sparkline.length > 0 && (
        <Sparkline
          data={sparkline}
          color={getSparklineColor()}
          trend={trend}
          showGradient={true}
          height={40}
        />
      )}
    </Card>
  );
};

