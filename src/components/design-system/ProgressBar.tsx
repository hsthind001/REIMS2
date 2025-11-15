import React from 'react';
import { motion } from 'framer-motion';
import styles from './ProgressBar.module.css';

export interface ProgressBarProps {
  value: number; // 0-100
  max?: number;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'primary';
  showLabel?: boolean;
  label?: string;
  height?: 'sm' | 'md' | 'lg';
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
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const classes = [
    styles.progressBar,
    styles[height],
    className
  ].filter(Boolean).join(' ');

  const trackClasses = [
    styles.track,
    styles[variant]
  ].filter(Boolean).join(' ');

  return (
    <div className={className || ''}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-text-secondary">{label || `${Math.round(percentage)}%`}</span>
          <span className="text-sm font-medium text-text-primary">{value} / {max}</span>
        </div>
      )}
      <div className={classes}>
        <motion.div
          className={trackClasses}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
};

