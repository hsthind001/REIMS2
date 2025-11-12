/**
 * Performance Monitoring Dashboard
 * Engine performance metrics and model monitoring
 */
import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface EngineMetrics {
  engine: string;
  avg_confidence: number;
  accuracy_rate: number;
  total_fields: number;
}

interface CacheStats {
  cache_hits: number;
  cache_misses: number;
  hit_rate_percentage: number;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function PerformanceMonitoring() {
  const [engineMetrics, setEngineMetrics] = useState<EngineMetrics[]>([]);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      // Fetch engine performance
      const metricsResponse = await fetch('/api/v1/monitoring/engine-performance');
      if (metricsResponse.ok) {
        const data = await metricsResponse.json();
        setEngineMetrics(data.engines || []);
      }

      // Fetch cache statistics
      const cacheResponse = await fetch('/api/v1/cache/stats');
      if (cacheResponse.ok) {
        const data = await cacheResponse.json();
        setCacheStats(data);
      }
    } catch (error) {
      console.error('Error fetching metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading performance metrics...</div>;
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Performance Monitoring</h1>
        <p className="text-gray-600 mt-2">Engine performance metrics and model health</p>
      </div>

      {/* Engine performance table */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">Engine Performance</h2>
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Engine</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Confidence</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Accuracy</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fields Processed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {engineMetrics.map((metric) => (
              <tr key={metric.engine}>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{metric.engine}</td>
                <td className="px-6 py-4 text-sm">
                  <div className="flex items-center">
                    <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${metric.avg_confidence * 100}%` }}
                      />
                    </div>
                    <span>{(metric.avg_confidence * 100).toFixed(1)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm">
                  {metric.accuracy_rate ? (metric.accuracy_rate * 100).toFixed(1) + '%' : 'N/A'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{metric.total_fields.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Cache statistics */}
      {cacheStats && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Cache Performance</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-500">Cache Hits</div>
              <div className="text-2xl font-bold text-green-600">{cacheStats.cache_hits}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Cache Misses</div>
              <div className="text-2xl font-bold text-orange-600">{cacheStats.cache_misses}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Hit Rate</div>
              <div className="text-2xl font-bold text-blue-600">{cacheStats.hit_rate_percentage.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

