/**
 * Period Comparison Component
 * 
 * Shows sparkline and delta comparison to prior period
 */
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from '../design-system';

interface PeriodComparisonProps {
  currentValue: number;
  priorValue?: number;
  label?: string;
  showSparkline?: boolean;
}

export default function PeriodComparison({
  currentValue,
  priorValue,
  label = 'Value',
  showSparkline = true
}: PeriodComparisonProps) {
  const change = priorValue !== undefined ? currentValue - priorValue : 0;
  const changePercent = priorValue !== undefined && priorValue !== 0 
    ? (change / Math.abs(priorValue)) * 100 
    : 0;

  const getTrendIcon = () => {
    if (change > 0) return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (change < 0) return <TrendingDown className="w-4 h-4 text-red-600" />;
    return <Minus className="w-4 h-4 text-gray-600" />;
  };

  const getTrendColor = () => {
    if (change > 0) return 'text-green-700';
    if (change < 0) return 'text-red-700';
    return 'text-gray-700';
  };

  // Simple sparkline (would be enhanced with actual chart library)
  const sparklineData = priorValue !== undefined 
    ? [priorValue, currentValue]
    : [currentValue];

  return (
    <Card className="p-4 border-l-4 border-green-500 bg-green-50">
      <div className="flex items-center gap-2 mb-3">
        {getTrendIcon()}
        <h3 className="text-sm font-semibold text-gray-900">What Changed</h3>
      </div>
      
      <div className="space-y-3">
        {/* Sparkline */}
        {showSparkline && sparklineData.length > 1 && (
          <div className="h-12 bg-white rounded border border-green-200 p-2 flex items-end gap-1">
            {sparklineData.map((value, index) => {
              const maxValue = Math.max(...sparklineData);
              const minValue = Math.min(...sparklineData);
              const range = maxValue - minValue || 1;
              const height = ((value - minValue) / range) * 100;
              
              return (
                <div
                  key={index}
                  className="flex-1 bg-green-500 rounded-t"
                  style={{ height: `${height}%` }}
                  title={`${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                />
              );
            })}
          </div>
        )}

        {/* Values */}
        <div className="space-y-2">
          {priorValue !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Prior Period:</span>
              <span className="font-medium">
                ${priorValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Current Period:</span>
            <span className="font-medium">
              ${currentValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          {priorValue !== undefined && (
            <div className={`flex justify-between text-sm pt-2 border-t ${getTrendColor()}`}>
              <span>Change:</span>
              <span className="font-semibold">
                {change > 0 ? '+' : ''}${change.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                {changePercent !== 0 && ` (${changePercent > 0 ? '+' : ''}${changePercent.toFixed(1)}%)`}
              </span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

