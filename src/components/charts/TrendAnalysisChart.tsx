/**
 * Trend Analysis Chart Component
 * 
 * Interactive charts for visualizing financial trends over time
 * Supports NOI, DSCR, occupancy rates, revenue, and other metrics
 */

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { TrendingUp, TrendingDown, Calendar, Download } from 'lucide-react';
import { Button } from '../design-system';
import { exportToExcel, exportToCSV } from '../../lib/exportUtils';

export interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
  period?: string;
}

export interface TrendAnalysisChartProps {
  /** Chart title */
  title: string;
  /** Data points for the chart */
  data: TrendDataPoint[];
  /** Metric name (e.g., 'NOI', 'DSCR', 'Occupancy') */
  metric: string;
  /** Chart type: 'line', 'area', or 'bar' */
  chartType?: 'line' | 'area' | 'bar';
  /** Y-axis label */
  yAxisLabel?: string;
  /** Format function for Y-axis values */
  yAxisFormatter?: (value: number) => string;
  /** Format function for tooltip values */
  tooltipFormatter?: (value: number) => string;
  /** Show trend indicators */
  showTrend?: boolean;
  /** Reference line value (e.g., threshold) */
  referenceLine?: number;
  /** Reference line label */
  referenceLineLabel?: string;
  /** Color scheme */
  color?: string;
  /** Enable zoom */
  enableZoom?: boolean;
  /** Show export buttons */
  showExport?: boolean;
  /** Height of the chart */
  height?: number;
}

export default function TrendAnalysisChart({
  title,
  data,
  metric,
  chartType = 'line',
  yAxisLabel,
  yAxisFormatter,
  tooltipFormatter,
  showTrend = true,
  referenceLine,
  referenceLineLabel,
  color = '#3b82f6',
  enableZoom = false,
  showExport = true,
  height = 300
}: TrendAnalysisChartProps) {
  const [trendDirection, setTrendDirection] = useState<'up' | 'down' | 'neutral'>('neutral');
  const [trendPercentage, setTrendPercentage] = useState<number>(0);

  useEffect(() => {
    if (data.length >= 2 && showTrend) {
      const firstValue = data[0].value;
      const lastValue = data[data.length - 1].value;
      
      if (firstValue !== 0) {
        const change = ((lastValue - firstValue) / Math.abs(firstValue)) * 100;
        setTrendPercentage(Math.abs(change));
        
        if (change > 0.1) {
          setTrendDirection('up');
        } else if (change < -0.1) {
          setTrendDirection('down');
        } else {
          setTrendDirection('neutral');
        }
      }
    }
  }, [data, showTrend]);

  const formatCurrency = (value: number): string => {
    if (Math.abs(value) >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    } else if (Math.abs(value) >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number): string => {
    return `${value.toFixed(2)}%`;
  };

  const defaultYAxisFormatter = (value: number): string => {
    if (metric.toLowerCase().includes('dscr') || metric.toLowerCase().includes('ratio')) {
      return value.toFixed(2);
    } else if (metric.toLowerCase().includes('occupancy') || metric.toLowerCase().includes('percent')) {
      return formatPercent(value);
    } else if (metric.toLowerCase().includes('noi') || metric.toLowerCase().includes('revenue') || metric.toLowerCase().includes('amount')) {
      return formatCurrency(value);
    }
    return value.toLocaleString();
  };

  const defaultTooltipFormatter = (value: number): string => {
    if (metric.toLowerCase().includes('dscr') || metric.toLowerCase().includes('ratio')) {
      return value.toFixed(2);
    } else if (metric.toLowerCase().includes('occupancy') || metric.toLowerCase().includes('percent')) {
      return formatPercent(value);
    } else if (metric.toLowerCase().includes('noi') || metric.toLowerCase().includes('revenue') || metric.toLowerCase().includes('amount')) {
      return formatCurrency(value);
    }
    return value.toLocaleString();
  };

  const yFormatter = yAxisFormatter || defaultYAxisFormatter;
  const tooltipFormatterFn = tooltipFormatter || defaultTooltipFormatter;

  const handleExportExcel = () => {
    const exportData = data.map(point => ({
      Date: point.date,
      Period: point.period || point.date,
      [metric]: point.value,
      Label: point.label || ''
    }));
    exportToExcel(exportData, `${metric.toLowerCase()}-trend-${new Date().toISOString().split('T')[0]}`, metric);
  };

  const handleExportCSV = () => {
    const exportData = data.map(point => ({
      Date: point.date,
      Period: point.period || point.date,
      [metric]: point.value,
      Label: point.label || ''
    }));
    exportToCSV(exportData, `${metric.toLowerCase()}-trend-${new Date().toISOString().split('T')[0]}`);
  };

  const renderChart = () => {
    const chartProps = {
      data: data.map(point => ({
        ...point,
        date: point.period || point.date
      })),
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    };

    if (chartType === 'area') {
      return (
        <AreaChart {...chartProps}>
          <defs>
            <linearGradient id={`color${metric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.8} />
              <stop offset="95%" stopColor={color} stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="date" 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
          />
          <YAxis 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
            tickFormatter={yFormatter}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '4px' }}
            formatter={(value: any) => [tooltipFormatterFn(value), metric]}
            labelStyle={{ color: '#374151', fontWeight: 600 }}
          />
          <Legend />
          {referenceLine && (
            <ReferenceLine 
              y={referenceLine} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              label={{ value: referenceLineLabel || 'Threshold', position: 'right' }}
            />
          )}
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fillOpacity={1}
            fill={`url(#color${metric})`}
            name={metric}
          />
        </AreaChart>
      );
    } else if (chartType === 'bar') {
      return (
        <BarChart {...chartProps}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="date" 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
          />
          <YAxis 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
            tickFormatter={yFormatter}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '4px' }}
            formatter={(value: any) => [tooltipFormatterFn(value), metric]}
            labelStyle={{ color: '#374151', fontWeight: 600 }}
          />
          <Legend />
          {referenceLine && (
            <ReferenceLine 
              y={referenceLine} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              label={{ value: referenceLineLabel || 'Threshold', position: 'right' }}
            />
          )}
          <Bar dataKey="value" fill={color} name={metric} radius={[8, 8, 0, 0]} />
        </BarChart>
      );
    } else {
      // Line chart (default)
      return (
        <LineChart {...chartProps}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="date" 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
          />
          <YAxis 
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 12 }}
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
            tickFormatter={yFormatter}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '4px' }}
            formatter={(value: any) => [tooltipFormatterFn(value), metric]}
            labelStyle={{ color: '#374151', fontWeight: 600 }}
          />
          <Legend />
          {referenceLine && (
            <ReferenceLine 
              y={referenceLine} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              label={{ value: referenceLineLabel || 'Threshold', position: 'right' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, r: 4 }}
            activeDot={{ r: 6 }}
            name={metric}
          />
        </LineChart>
      );
    }
  };

  if (data.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center text-gray-500 py-8">
          No data available for trend analysis
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">{title}</h3>
          {showTrend && trendDirection !== 'neutral' && (
            <div className={`flex items-center gap-1 text-sm ${
              trendDirection === 'up' ? 'text-green-600' : 'text-red-600'
            }`}>
              {trendDirection === 'up' ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span className="font-medium">
                {trendPercentage.toFixed(1)}% {trendDirection === 'up' ? 'increase' : 'decrease'}
              </span>
            </div>
          )}
        </div>
        {showExport && (
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportExcel}
              className="flex items-center gap-1"
            >
              <Download className="w-4 h-4" />
              Excel
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportCSV}
              className="flex items-center gap-1"
            >
              <Download className="w-4 h-4" />
              CSV
            </Button>
          </div>
        )}
      </div>
      
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
      
      {data.length > 0 && (
        <div className="mt-4 text-sm text-gray-600 flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          <span>
            {data.length} data points from {data[0].date} to {data[data.length - 1].date}
          </span>
        </div>
      )}
    </div>
  );
}

