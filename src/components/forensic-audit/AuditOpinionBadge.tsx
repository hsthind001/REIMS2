/**
 * Audit Opinion Badge Component
 *
 * Displays UNQUALIFIED/QUALIFIED/ADVERSE audit opinion with styling
 */

import { Shield, ShieldAlert, ShieldX } from 'lucide-react';
import type { AuditOpinion } from '../../lib/forensic_audit';

interface AuditOpinionBadgeProps {
  opinion: AuditOpinion;
  size?: 'sm' | 'md' | 'lg';
  showDescription?: boolean;
  className?: string;
}

export default function AuditOpinionBadge({
  opinion,
  size = 'md',
  showDescription = false,
  className = '',
}: AuditOpinionBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const iconSizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const getOpinionConfig = () => {
    switch (opinion) {
      case 'UNQUALIFIED':
        return {
          icon: Shield,
          color: 'text-green-700',
          bgColor: 'bg-green-100',
          borderColor: 'border-green-300',
          label: 'Unqualified',
          description: 'Clean opinion - all tests passed',
        };
      case 'QUALIFIED':
        return {
          icon: ShieldAlert,
          color: 'text-yellow-700',
          bgColor: 'bg-yellow-100',
          borderColor: 'border-yellow-300',
          label: 'Qualified',
          description: 'Some issues but manageable',
        };
      case 'ADVERSE':
        return {
          icon: ShieldX,
          color: 'text-red-700',
          bgColor: 'bg-red-100',
          borderColor: 'border-red-300',
          label: 'Adverse',
          description: 'Significant issues requiring attention',
        };
    }
  };

  const config = getOpinionConfig();
  const Icon = config.icon;

  return (
    <div className={`inline-flex flex-col gap-1 ${className}`}>
      <div
        className={`inline-flex items-center gap-2 ${sizeClasses[size]} ${config.bgColor} ${config.color} border ${config.borderColor} rounded-lg font-semibold`}
      >
        <Icon className={iconSizeClasses[size]} />
        <span>{config.label}</span>
      </div>
      {showDescription && (
        <div className="text-xs text-gray-600">
          {config.description}
        </div>
      )}
    </div>
  );
}
