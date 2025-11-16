import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

export interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  showGradient?: boolean;
  trend?: 'up' | 'down' | 'neutral';
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  color = '#0ea5e9', // Default: sky-500
  height = 32,
  showGradient = true,
  trend
}) => {
  // Return null if no data
  if (!data || data.length === 0) {
    return null;
  }

  // Transform data for recharts format
  const chartData = data.map((value, index) => ({
    index,
    value: value || 0
  }));

  // Auto-detect trend if not provided
  let lineColor = color;
  if (trend) {
    if (trend === 'up') lineColor = '#10b981'; // green-500
    if (trend === 'down') lineColor = '#ef4444'; // red-500
    if (trend === 'neutral') lineColor = '#64748b'; // slate-500
  } else if (data.length >= 2) {
    // Auto-detect trend from first and last values
    const first = data[0] || 0;
    const last = data[data.length - 1] || 0;
    if (last > first * 1.05) lineColor = '#10b981';
    if (last < first * 0.95) lineColor = '#ef4444';
  }

  // Calculate min/max for Y-axis domain
  const values = data.filter(v => v !== null && v !== undefined);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue;
  const padding = range * 0.1; // 10% padding

  return (
    <div style={{ width: '100%', height: `${height}px`, marginTop: '0.5rem' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <YAxis
            domain={[minValue - padding, maxValue + padding]}
            hide
          />
          {showGradient && (
            <defs>
              <linearGradient id={`sparkline-gradient-${lineColor.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={0.3} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0.05} />
              </linearGradient>
            </defs>
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={true}
            animationDuration={800}
            animationEasing="ease-in-out"
            fill={showGradient ? `url(#sparkline-gradient-${lineColor.replace('#', '')})` : 'none'}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Compact sparkline for table cells
export const CompactSparkline: React.FC<Omit<SparklineProps, 'height'>> = (props) => {
  return <Sparkline {...props} height={24} showGradient={false} />;
};
