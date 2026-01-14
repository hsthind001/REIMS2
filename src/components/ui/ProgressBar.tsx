import React from 'react';
import { motion } from 'framer-motion';
import './progress-bar.css';

export interface ProgressBarProps {
  value: number; // 0-100
  max?: number;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'primary' | 'purple';
  showLabel?: boolean;
  label?: string;
  height?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  variant = 'success',
  showLabel = false,
  label,
  height = 'md',
  className = '',
}) => {
  // Ensure value and max are valid numbers, defaulting to 0 if NaN/null/undefined
  const safeValue = isNaN(value) || value === null || value === undefined ? 0 : Number(value);
  const safeMax = isNaN(max) || max === null || max === undefined || max === 0 ? 100 : Number(max);
  const percentage = safeMax > 0 ? Math.min(Math.max((safeValue / safeMax) * 100, 0), 100) : 0;

  const containerClasses = [
    'ui-progress-bar',
    `ui-progress-bar-${height}`,
    `ui-progress-bar-${variant}`, // Added for variant-specific container styling if needed, but mainly used for track
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={className ? `w-full ${className}` : 'w-full'}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-500">{label || `${Math.round(percentage)}%`}</span>
          <span className="text-sm font-medium text-gray-900">{value} / {max}</span>
        </div>
      )}
      <div className={`ui-progress-bar ui-progress-bar-${height}`}>
        <motion.div
          className="ui-progress-bar-track"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
};
