/**
 * Portfolio Benchmarks Component
 * 
 * Displays cross-property portfolio analytics:
 * - Cross-property benchmarks chart
 * - Property ranking table
 * - Outlier highlighting
 */

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { TrendingUp, TrendingDown, Award, AlertTriangle } from 'lucide-react'
import { anomaliesService, type PortfolioBenchmark } from '../../lib/anomalies'

interface PortfolioBenchmarksProps {
  propertyId: number
  accountCode: string
  metricType?: string
  className?: string
}

export function PortfolioBenchmarks({
  propertyId,
  accountCode,
  metricType = 'balance_sheet',
  className = '',
}: PortfolioBenchmarksProps) {
  const [benchmark, setBenchmark] = useState<PortfolioBenchmark | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBenchmark()
  }, [propertyId, accountCode, metricType])

  const loadBenchmark = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await anomaliesService.getPropertyBenchmark(propertyId, accountCode, metricType)
      setBenchmark(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio benchmark')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading benchmarks...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <AlertTriangle size={20} />
            <span className="font-medium">Error loading benchmarks</span>
          </div>
          <p className="text-red-600 text-sm mt-2">{error}</p>
        </div>
      </div>
    )
  }

  if (!benchmark) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="text-center py-8">
          <Award className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No benchmark data available for this account.</p>
        </div>
      </div>
    )
  }

  const percentileRank = benchmark.percentile_rank
  const isOutlier = percentileRank < 5 || percentileRank > 95
  const isTopPerformer = percentileRank > 90
  const isBottomPerformer = percentileRank < 10

  // Prepare chart data
  const chartData = [
    {
      name: '25th Percentile',
      value: benchmark.percentile_25,
      color: '#e5e7eb',
    },
    {
      name: 'Median',
      value: benchmark.percentile_75,
      color: '#3b82f6',
    },
    {
      name: '75th Percentile',
      value: benchmark.percentile_75,
      color: '#60a5fa',
    },
    {
      name: '90th Percentile',
      value: benchmark.percentile_90,
      color: '#93c5fd',
    },
    {
      name: '95th Percentile',
      value: benchmark.percentile_95,
      color: '#dbeafe',
    },
  ]

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Award className="h-5 w-5 text-blue-500" />
          Portfolio Benchmark
        </h3>
        <div className="flex items-center gap-2">
          {isTopPerformer && (
            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded flex items-center gap-1">
              <TrendingUp size={12} />
              Top Performer
            </span>
          )}
          {isBottomPerformer && (
            <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded flex items-center gap-1">
              <TrendingDown size={12} />
              Needs Attention
            </span>
          )}
          {isOutlier && (
            <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded flex items-center gap-1">
              <AlertTriangle size={12} />
              Outlier
            </span>
          )}
        </div>
      </div>

      {/* Percentile Rank */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Percentile Rank</span>
          <span className="text-2xl font-bold text-gray-900">{percentileRank.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className={`h-4 rounded-full transition-all ${
              isTopPerformer
                ? 'bg-green-500'
                : isBottomPerformer
                ? 'bg-red-500'
                : 'bg-blue-500'
            }`}
            style={{ width: `${percentileRank}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          This property ranks in the {percentileRank.toFixed(1)}th percentile among {benchmark.property_count} properties
        </p>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Mean</div>
          <div className="text-lg font-semibold text-gray-900">
            ${benchmark.benchmark_mean.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Median</div>
          <div className="text-lg font-semibold text-gray-900">
            ${benchmark.benchmark_median.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Std Dev</div>
          <div className="text-lg font-semibold text-gray-900">
            ${benchmark.benchmark_std.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Properties</div>
          <div className="text-lg font-semibold text-gray-900">{benchmark.property_count}</div>
        </div>
      </div>

      {/* Percentile Distribution Chart */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Percentile Distribution</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip
              formatter={(value: number) => [
                `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
                'Value',
              ]}
            />
            <Bar dataKey="value">
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Percentile Values */}
      <div className="pt-4 border-t border-gray-200">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Percentile Values</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <div className="text-xs text-gray-500 mb-1">25th</div>
            <div className="text-sm font-medium text-gray-900">
              ${benchmark.percentile_25.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">75th</div>
            <div className="text-sm font-medium text-gray-900">
              ${benchmark.percentile_75.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">90th</div>
            <div className="text-sm font-medium text-gray-900">
              ${benchmark.percentile_90.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">95th</div>
            <div className="text-sm font-medium text-gray-900">
              ${benchmark.percentile_95.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

