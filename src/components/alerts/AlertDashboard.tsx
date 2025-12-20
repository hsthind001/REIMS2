/**
 * Alert Dashboard Component
 * Displays comprehensive alert overview with widgets and charts
 */
import { useState, useEffect } from 'react';
import { AlertService, AlertSummary, AlertTrendsResponse } from '../../lib/alerts';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

interface AlertDashboardProps {
  propertyId?: number;
  onAlertClick?: (alertId: number) => void;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function AlertDashboard({ propertyId, onAlertClick }: AlertDashboardProps) {
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [trends, setTrends] = useState<AlertTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(30);

  useEffect(() => {
    loadDashboardData();
  }, [propertyId, timeRange]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryData, trendsData] = await Promise.all([
        AlertService.getSummary({ property_id: propertyId, days: timeRange }),
        AlertService.getTrends({ property_id: propertyId, days: timeRange })
      ]);

      setSummary(summaryData);
      setTrends(trendsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc3545' }}>
        <p>Error: {error}</p>
        <button onClick={loadDashboardData} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
          Retry
        </button>
      </div>
    );
  }

  if (!summary) {
    return <div style={{ padding: '2rem' }}>No data available</div>;
  }

  // Prepare chart data
  const trendData = trends?.trends.map(t => ({
    date: new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    count: t.count
  })) || [];

  const severityData = Object.entries(summary.by_severity).map(([name, value]) => ({
    name: name.toUpperCase(),
    value
  }));

  const typeData = Object.entries(summary.by_type).slice(0, 5).map(([name, value]) => ({
    name: name.replace(/_/g, ' '),
    value
  }));

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
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Summary Widgets */}
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
          borderLeft: '4px solid #dc3545'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Total Alerts</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {summary.total_alerts}
          </div>
        </div>

        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #ffc107'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Active Alerts</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {summary.active_alerts}
          </div>
        </div>

        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #dc3545'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Critical/Urgent</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#333' }}>
            {summary.critical_active}
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
            {(summary.by_status.RESOLVED || 0)}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        {/* Alert Trends */}
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Alert Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#0088FE" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Distribution */}
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alert Type Distribution */}
      <div style={{
        padding: '1.5rem',
        background: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        marginBottom: '2rem'
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Top Alert Types</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={typeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#0088FE" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Status Breakdown */}
      <div style={{
        padding: '1.5rem',
        background: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Status Breakdown</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          {Object.entries(summary.by_status).map(([status, count]) => (
            <div key={status} style={{
              padding: '1rem',
              background: '#f8f9fa',
              borderRadius: '4px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#333' }}>{count}</div>
              <div style={{ fontSize: '0.875rem', color: '#666', textTransform: 'capitalize' }}>
                {status.replace(/_/g, ' ')}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

