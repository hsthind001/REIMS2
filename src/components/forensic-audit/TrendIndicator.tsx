/**
 * Trend Indicator Component
 *
 * Displays UP/DOWN/STABLE trend with arrow icons
 */

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { TrendDirection } from '../../lib/forensic_audit';

interface TrendIndicatorProps {
  trend: TrendDirection;
  value?: number | null;
  previousValue?: number | null;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function TrendIndicator({
  trend,
  value,
  previousValue,
  showLabel = false,
  size = 'md',
  className = '',
}: TrendIndicatorProps) {
  const sizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const getTrendConfig = () => {
    switch (trend) {
      case 'UP':
        return {
          icon: TrendingUp,
          color: 'text-green-600',
          label: 'Improving',
        };
      case 'DOWN':
        return {
          icon: TrendingDown,
          color: 'text-red-600',
          label: 'Declining',
        };
      case 'STABLE':
        return {
          icon: Minus,
          color: 'text-gray-600',
          label: 'Stable',
        };
    }
  };

  const config = getTrendConfig();
  const Icon = config.icon;

  // Calculate change percentage if values provided
  let changeText = '';
  if (value !== null && value !== undefined && previousValue !== null && previousValue !== undefined && previousValue !== 0) {
    const change = ((value - previousValue) / previousValue) * 100;
    changeText = `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`;
  }

  if (showLabel) {
    return (
      <div className={`inline-flex items-center gap-1.5 ${className}`}>
        <Icon className={`${sizeClasses[size]} ${config.color}`} />
        <span className={`font-medium ${config.color} ${textSizeClasses[size]}`}>
          {config.label}
          {changeText && ` (${changeText})`}
        </span>
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center gap-1 ${className}`}>
      <Icon className={`${sizeClasses[size]} ${config.color}`} />
      {changeText && (
        <span className={`${textSizeClasses[size]} ${config.color}`}>
          {changeText}
        </span>
      )}
    </div>
  );
}
