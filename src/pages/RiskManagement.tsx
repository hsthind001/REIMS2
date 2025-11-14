import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface Alert {
  id: number
  property_id: number
  alert_type: string
  severity: string
  title: string
  status: string
  threshold_value: number
  actual_value: number
  created_at: string
}

interface WorkflowLock {
  id: number
  property_id: number
  lock_reason: string
  status: string
  requires_committee_approval: boolean
  created_at: string
}

interface Anomaly {
  metric_name: string
  period_name: string
  value: number
  z_score: number
  severity: string
}

export default function RiskManagement() {
  const [activeTab, setActiveTab] = useState<'alerts' | 'locks' | 'anomalies'>('alerts')
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [locks, setLocks] = useState<WorkflowLock[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dashboardStats, setDashboardStats] = useState<any>(null)

  useEffect(() => {
    fetchProperties()
    fetchDashboardStats()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchAlerts(selectedProperty)
      fetchLocks(selectedProperty)
      fetchAnomalies(selectedProperty)
    }
  }, [selectedProperty])

  const fetchProperties = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/properties`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setProperties(data.properties || [])
        if (data.properties && data.properties.length > 0) {
          setSelectedProperty(data.properties[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to fetch properties:', err)
    }
  }

  const fetchDashboardStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/dashboard/summary`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setDashboardStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch dashboard stats:', err)
    }
  }

  const fetchAlerts = async (propertyId: number) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/properties/${propertyId}/alerts`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setAlerts(data.alerts || [])
      }
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchLocks = async (propertyId: number) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/workflow-locks/properties/${propertyId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setLocks(data.locks || [])
      }
    } catch (err) {
      console.error('Failed to fetch locks:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchAnomalies = async (propertyId: number) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/statistical-anomalies/properties/${propertyId}/comprehensive-scan`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        const allAnomalies = [
          ...(data.zscore_anomalies || []),
          ...(data.cusum_anomalies || [])
        ]
        setAnomalies(allAnomalies)
      }
    } catch (err) {
      console.error('Failed to fetch anomalies:', err)
    } finally {
      setLoading(false)
    }
  }

  const acknowledgeAlert = async (alertId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: 1, notes: 'Acknowledged from UI' })
      })
      if (response.ok && selectedProperty) {
        fetchAlerts(selectedProperty)
      }
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'urgent':
        return 'error'
      case 'warning':
        return 'warning'
      default:
        return 'info'
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">🛡️ Risk Management</h1>
          <p className="page-subtitle">Comprehensive Risk Monitoring & Workflow Controls</p>
        </div>
      </div>

      {/* Dashboard Stats */}
      {dashboardStats && (
        <div className="stats-grid">
          <div className="stat-card stat-error">
            <div className="stat-icon">🚨</div>
            <div className="stat-info">
              <div className="stat-value">{dashboardStats.total_critical_alerts || 0}</div>
              <div className="stat-label">Critical Alerts</div>
            </div>
          </div>
          <div className="stat-card stat-warning">
            <div className="stat-icon">⚠️</div>
            <div className="stat-info">
              <div className="stat-value">{dashboardStats.total_active_alerts || 0}</div>
              <div className="stat-label">Active Alerts</div>
            </div>
          </div>
          <div className="stat-card stat-info">
            <div className="stat-icon">🔒</div>
            <div className="stat-info">
              <div className="stat-value">{dashboardStats.total_active_locks || 0}</div>
              <div className="stat-label">Active Locks</div>
            </div>
          </div>
          <div className="stat-card stat-success">
            <div className="stat-icon">✅</div>
            <div className="stat-info">
              <div className="stat-value">{dashboardStats.properties_with_good_dscr || 0}</div>
              <div className="stat-label">Healthy Properties</div>
            </div>
          </div>
        </div>
      )}

      {/* Property Selector */}
      <div className="card">
        <h3 className="card-title">Select Property</h3>
        <select
          className="select-input"
          value={selectedProperty || ''}
          onChange={(e) => setSelectedProperty(Number(e.target.value))}
        >
          <option value="">Choose a property...</option>
          {properties.map(p => (
            <option key={p.id} value={p.id}>
              {p.property_name} - {p.address}
            </option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          🚨 Risk Alerts ({alerts.length})
        </button>
        <button
          className={`tab ${activeTab === 'locks' ? 'active' : ''}`}
          onClick={() => setActiveTab('locks')}
        >
          🔒 Workflow Locks ({locks.length})
        </button>
        <button
          className={`tab ${activeTab === 'anomalies' ? 'active' : ''}`}
          onClick={() => setActiveTab('anomalies')}
        >
          📊 Anomalies ({anomalies.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'alerts' && (
        <div className="card">
          <h3 className="card-title">Risk Alerts</h3>
          {alerts.length > 0 ? (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Threshold</th>
                    <th>Actual</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((alert) => (
                    <tr key={alert.id}>
                      <td>{alert.id}</td>
                      <td>{alert.alert_type}</td>
                      <td>
                        <span className={`badge badge-${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td>{alert.title}</td>
                      <td>{alert.threshold_value?.toFixed(2)}</td>
                      <td>{alert.actual_value?.toFixed(2)}</td>
                      <td>
                        <span className={`badge badge-${alert.status === 'active' ? 'warning' : 'success'}`}>
                          {alert.status}
                        </span>
                      </td>
                      <td>{new Date(alert.created_at).toLocaleDateString()}</td>
                      <td>
                        {alert.status === 'active' && (
                          <button
                            className="btn-sm btn-primary"
                            onClick={() => acknowledgeAlert(alert.id)}
                          >
                            Acknowledge
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <p>✅ No active alerts for this property</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'locks' && (
        <div className="card">
          <h3 className="card-title">Workflow Locks</h3>
          {locks.length > 0 ? (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Requires Approval</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {locks.map((lock) => (
                    <tr key={lock.id}>
                      <td>{lock.id}</td>
                      <td>{lock.lock_reason}</td>
                      <td>
                        <span className={`badge badge-${lock.status === 'active' ? 'error' : 'success'}`}>
                          {lock.status}
                        </span>
                      </td>
                      <td>
                        {lock.requires_committee_approval ? '✓' : '✗'}
                      </td>
                      <td>{new Date(lock.created_at).toLocaleDateString()}</td>
                      <td>
                        {lock.status === 'active' && (
                          <button className="btn-sm btn-warning">
                            Request Release
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <p>✅ No active workflow locks for this property</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'anomalies' && (
        <div className="card">
          <h3 className="card-title">Statistical Anomalies</h3>
          {anomalies.length > 0 ? (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Period</th>
                    <th>Value</th>
                    <th>Z-Score</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((anomaly, idx) => (
                    <tr key={idx}>
                      <td>{anomaly.metric_name}</td>
                      <td>{anomaly.period_name}</td>
                      <td>{anomaly.value?.toLocaleString()}</td>
                      <td>{anomaly.z_score?.toFixed(2)}</td>
                      <td>
                        <span className={`badge badge-${getSeverityColor(anomaly.severity)}`}>
                          {anomaly.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <p>✅ No anomalies detected for this property</p>
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="card">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading risk data...</p>
          </div>
        </div>
      )}
    </div>
  )
}
