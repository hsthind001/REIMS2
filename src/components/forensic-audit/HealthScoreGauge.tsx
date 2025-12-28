/**
 * Health Score Gauge Component
 *
 * Displays a circular gauge for 0-100 health scores with grade
 */

import { useMemo } from 'react';

interface HealthScoreGaugeProps {
  score: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  showGrade?: boolean;
  className?: string;
}

export default function HealthScoreGauge({
  score,
  size = 'md',
  showGrade = true,
  className = '',
}: HealthScoreGaugeProps) {
  const sizeConfig = {
    sm: { diameter: 80, strokeWidth: 8, fontSize: 'text-lg' },
    md: { diameter: 120, strokeWidth: 12, fontSize: 'text-2xl' },
    lg: { diameter: 160, strokeWidth: 16, fontSize: 'text-3xl' },
  };

  const config = sizeConfig[size];
  const radius = (config.diameter - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(score, 0), 100);
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const { color, grade } = useMemo(() => {
    if (score >= 90) return { color: '#10b981', grade: 'A' }; // green-500
    if (score >= 80) return { color: '#3b82f6', grade: 'B' }; // blue-500
    if (score >= 70) return { color: '#f59e0b', grade: 'C' }; // amber-500
    if (score >= 60) return { color: '#f97316', grade: 'D' }; // orange-500
    return { color: '#ef4444', grade: 'F' }; // red-500
  }, [score]);

  return (
    <div className={`inline-flex flex-col items-center ${className}`}>
      <div className="relative" style={{ width: config.diameter, height: config.diameter }}>
        {/* Background circle */}
        <svg className="transform -rotate-90" width={config.diameter} height={config.diameter}>
          <circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke="#e5e7eb"
            strokeWidth={config.strokeWidth}
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke={color}
            strokeWidth={config.strokeWidth}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className={`font-bold ${config.fontSize}`} style={{ color }}>
            {Math.round(score)}
          </div>
          {showGrade && (
            <div className="text-sm text-gray-600 mt-1">
              Grade: {grade}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
