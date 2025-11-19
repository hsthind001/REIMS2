import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from './Card';
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

  // Simple sparkline rendering
  const renderSparkline = () => {
    if (!sparkline || sparkline.length === 0) return null;
    
    const max = Math.max(...sparkline);
    const min = Math.min(...sparkline);
    const range = max - min || 1;
    
    return (
      <div className={styles.sparkline}>
        {sparkline.map((point, index) => {
          const height = ((point - min) / range) * 100;
          return (
            <div
              key={index}
              className={styles.sparklineBar}
              style={{ height: `${Math.max(height, 5)}%` }}
            />
          );
        })}
      </div>
    );
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

      {renderSparkline()}
    </Card>
  );
};

