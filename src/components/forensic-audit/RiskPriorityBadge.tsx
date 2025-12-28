/**
 * Risk Priority Badge Component
 *
 * Displays HIGH/MODERATE/LOW risk severity with color coding
 */

import { AlertCircle } from 'lucide-react';
import type { RiskSeverity } from '../../lib/forensic_audit';

interface RiskPriorityBadgeProps {
  severity: RiskSeverity;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function RiskPriorityBadge({
  severity,
  size = 'md',
  className = '',
}: RiskPriorityBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const iconSizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  const getSeverityConfig = () => {
    switch (severity) {
      case 'HIGH':
        return {
          color: 'text-red-700',
          bgColor: 'bg-red-100',
          borderColor: 'border-red-300',
          label: 'High',
        };
      case 'MODERATE':
        return {
          color: 'text-yellow-700',
          bgColor: 'bg-yellow-100',
          borderColor: 'border-yellow-300',
          label: 'Moderate',
        };
      case 'LOW':
        return {
          color: 'text-blue-700',
          bgColor: 'bg-blue-100',
          borderColor: 'border-blue-300',
          label: 'Low',
        };
    }
  };

  const config = getSeverityConfig();

  return (
    <div
      className={`inline-flex items-center gap-1 ${sizeClasses[size]} ${config.bgColor} ${config.color} border ${config.borderColor} rounded-md font-medium ${className}`}
    >
      <AlertCircle className={iconSizeClasses[size]} />
      <span>{config.label}</span>
    </div>
  );
}
