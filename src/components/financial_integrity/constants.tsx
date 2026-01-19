import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

export const ReconciliationColors = {
  perfectMatch: {
    bg: 'rgba(16, 185, 129, 0.1)',
    border: '#10B981',
    text: '#065F46',
    icon: '#059669',
    gradient: 'from-emerald-400 to-emerald-600'
  },
  
  acceptableVariance: {
    bg: 'rgba(59, 130, 246, 0.1)',
    border: '#3B82F6',
    text: '#1E40AF',
    icon: '#2563EB',
    gradient: 'from-blue-400 to-blue-600'
  },
  
  timingVariance: {
    bg: 'rgba(245, 158, 11, 0.1)',
    border: '#F59E0B',
    text: '#92400E',
    icon: '#D97706',
    gradient: 'from-amber-400 to-amber-600'
  },
  
  discrepancy: {
    bg: 'rgba(239, 68, 68, 0.1)',
    border: '#EF4444',
    text: '#991B1B',
    icon: '#DC2626',
    gradient: 'from-red-400 to-red-600'
  },
  
  notApplicable: {
    bg: 'rgba(107, 114, 128, 0.05)',
    border: '#D1D5DB',
    text: '#6B7280',
    icon: '#9CA3AF',
    gradient: 'from-gray-400 to-gray-600'
  }
};

export const TrendIndicator = ({ value }: { value: number }) => {
    if (value > 0) return <ArrowUp className="w-4 h-4 text-green-500" />;
    if (value < 0) return <ArrowDown className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
};

export const statusConfig = {
    excellent: { color: 'green', label: 'Excellent', range: [90, 100] },
    stable: { color: 'blue', label: 'Stable', range: [75, 89] },
    attention: { color: 'amber', label: 'Attention Needed', range: [60, 74] },
    critical: { color: 'red', label: 'Critical', range: [0, 59] }
};

export const getStatusForScore = (score: number) => {
    if (score >= 90) return statusConfig.excellent;
    if (score >= 75) return statusConfig.stable;
    if (score >= 60) return statusConfig.attention;
    return statusConfig.critical;
};
