/**
 * Anomaly Detection Dashboard
 * Statistical and ML-based anomaly visualization
 */
import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Anomaly {
  id: number;
  type: string;
  severity: string;
  field_name: string;
  value: number;
  message: string;
  created_at: string;
}

export default function AnomalyDashboard() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState<any[]>([]);

  useEffect(() => {
    fetchAnomalies();
  }, []);

  const fetchAnomalies = async () => {
    try {
      const response = await fetch('/api/v1/anomalies');
      if (response.ok) {
        const data = await response.json();
        setAnomalies(data);
        
        // Prepare chart data
        const typeCounts = data.reduce((acc: any, anomaly: Anomaly) => {
          acc[anomaly.type] = (acc[anomaly.type] || 0) + 1;
          return acc;
        }, {});
        
        setChartData(Object.entries(typeCounts).map(([type, count]) => ({
          type,
          count
        })));
      }
    } catch (error) {
      console.error('Error fetching anomalies:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading anomalies...</div>;
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Anomaly Detection Dashboard</h1>
        <p className="text-gray-600 mt-2">Statistical and ML-based anomaly visualization</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500">Total Anomalies</div>
          <div className="text-3xl font-bold text-gray-900">{anomalies.length}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500">Critical</div>
          <div className="text-3xl font-bold text-red-600">
            {anomalies.filter(a => a.severity === 'critical').length}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500">High</div>
          <div className="text-3xl font-bold text-orange-600">
            {anomalies.filter(a => a.severity === 'high').length}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500">Medium</div>
          <div className="text-3xl font-bold text-yellow-600">
            {anomalies.filter(a => a.severity === 'medium').length}
          </div>
        </div>
      </div>

      {/* Anomaly chart */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">Anomaly Distribution by Type</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Anomaly table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Field</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Detected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {anomalies.map((anomaly) => (
              <tr key={anomaly.id}>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{anomaly.type}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    anomaly.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    anomaly.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    anomaly.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {anomaly.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">{anomaly.field_name}</td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {anomaly.value?.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{anomaly.message}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(anomaly.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

