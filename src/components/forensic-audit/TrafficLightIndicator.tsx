/**
 * Traffic Light Indicator Component
 *
 * Displays GREEN/YELLOW/RED status with icon and color
 */

import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import type { TrafficLightStatus } from '../../lib/forensic_audit';

interface TrafficLightIndicatorProps {
  status: TrafficLightStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export default function TrafficLightIndicator({
  status,
  size = 'md',
  showLabel = false,
  className = '',
}: TrafficLightIndicatorProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const getStatusConfig = () => {
    switch (status) {
      case 'GREEN':
        return {
          icon: CheckCircle,
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          label: 'Pass',
        };
      case 'YELLOW':
        return {
          icon: AlertTriangle,
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-100',
          label: 'Warning',
        };
      case 'RED':
        return {
          icon: XCircle,
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          label: 'Fail',
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  if (showLabel) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${config.bgColor} ${className}`}>
        <Icon className={`${sizeClasses[size]} ${config.color}`} />
        <span className={`font-medium ${config.color} ${textSizeClasses[size]}`}>
          {config.label}
        </span>
      </div>
    );
  }

  return (
    <Icon className={`${sizeClasses[size]} ${config.color} ${className}`} />
  );
}
