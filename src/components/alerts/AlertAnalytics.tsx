/**
 * Alert Analytics Component
 * Comprehensive analytics and insights for alerts
 */
import { useState, useEffect } from 'react';
import { AlertService, type AlertAnalytics } from '../../lib/alerts';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

interface AlertAnalyticsProps {
  propertyId?: number;
}

export default function AlertAnalytics({ propertyId }: AlertAnalyticsProps) {
  const [analytics, setAnalytics] = useState<AlertAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(90);

  useEffect(() => {
    loadAnalytics();
  }, [propertyId, timeRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await AlertService.getAnalytics({
        property_id: propertyId,
        days: timeRange
      });

      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics');
      console.error('Error loading analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc3545' }}>
        <p>Error: {error}</p>
        <button onClick={loadAnalytics} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
          Retry
        </button>
      </div>
    );
  }

  if (!analytics) {
    return <div style={{ padding: '2rem' }}>No analytics data available</div>;
  }

  // Prepare chart data
  const typeFrequencyData = Object.entries(analytics.type_frequency)
    .map(([name, value]) => ({
      name: name.replace(/_/g, ' '),
      count: value
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const propertyDistributionData = analytics.property_distribution
    ? Object.entries(analytics.property_distribution)
        .map(([id, count]) => ({
          property: `Property ${id}`,
          count
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10)
    : [];

  return (
    <div style={{ padding: '1.5rem' }}>
      {/* Time Range Selector */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <label>Time Range:</label>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(Number(e.target.value))}
          style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
        >
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={180}>Last 6 months</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #0088FE'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Total Alerts</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {analytics.total_alerts}
          </div>
        </div>

        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #28a745'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Resolved</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {analytics.resolved_count}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
            {analytics.total_alerts > 0
              ? `${((analytics.resolved_count / analytics.total_alerts) * 100).toFixed(1)}% resolution rate`
              : 'N/A'}
          </div>
        </div>

        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #ffc107'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Avg Resolution Time</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {analytics.average_resolution_hours
              ? `${(analytics.average_resolution_hours / 24).toFixed(1)} days`
              : 'N/A'}
          </div>
          {analytics.average_resolution_hours && (
            <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
              {analytics.average_resolution_hours.toFixed(1)} hours
            </div>
          )}
        </div>

        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #dc3545'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Active Alerts</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {analytics.total_alerts - analytics.resolved_count}
          </div>
        </div>
      </div>

      {/* Alert Type Frequency */}
      <div style={{
        padding: '1.5rem',
        background: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        marginBottom: '2rem'
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Alert Type Frequency</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={typeFrequencyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#0088FE" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Property Distribution (if available) */}
      {propertyDistributionData.length > 0 && (
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '2rem'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Alerts by Property</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={propertyDistributionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="property" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#00C49F" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Insights */}
      <div style={{
        padding: '1.5rem',
        background: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Insights</h3>
        <ul style={{ margin: 0, paddingLeft: '1.5rem', lineHeight: '1.8' }}>
          {analytics.average_resolution_hours && analytics.average_resolution_hours < 48 && (
            <li>Excellent response time: Alerts are being resolved quickly (under 48 hours on average)</li>
          )}
          {analytics.average_resolution_hours && analytics.average_resolution_hours > 72 && (
            <li>Attention needed: Average resolution time exceeds 72 hours. Consider process improvements.</li>
          )}
          {analytics.resolved_count / analytics.total_alerts > 0.8 && (
            <li>High resolution rate: Over 80% of alerts have been resolved</li>
          )}
          {analytics.resolved_count / analytics.total_alerts < 0.5 && (
            <li>Low resolution rate: Less than 50% of alerts have been resolved. Review alert management process.</li>
          )}
          {typeFrequencyData.length > 0 && (
            <li>
              Most common alert type: {typeFrequencyData[0].name} ({typeFrequencyData[0].count} occurrences)
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

