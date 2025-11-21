import { useState, useEffect } from 'react'
import '../App.css'
import { propertyService } from '../lib/property'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface Alert {
  id: number
  property_id: number
  alert_type: string
  severity: string
  title: string
  description?: string
  status: string
  threshold_value?: number
  actual_value?: number
  threshold_unit?: string
  created_at: string
  acknowledged_at?: string
  resolved_at?: string
  acknowledged_by?: number
  resolved_by?: number
  document_id?: number
  file_name?: string
  document_type?: string
  field_name?: string
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
  type: string
  severity: string
  record_id?: number
  field_name?: string
  value?: number
  message: string
  details: {
    property_code?: string
    property_id?: number
    period?: string
    period_id?: number
    document_id?: number
    file_name?: string
    document_type?: string
    upload_date?: string
    expected_value?: string
    field_value?: string
    z_score?: number
    percentage_change?: number
    confidence?: number
    // Underlying calculation data
    total_current_assets?: number
    total_current_liabilities?: number
    total_liabilities?: number
    total_equity?: number
    total_assets?: number
    total_units?: number
    occupied_units?: number
  }
}

export default function RiskManagement() {
  const [activeTab, setActiveTab] = useState<'alerts' | 'locks' | 'anomalies'>('alerts')
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [locks, setLocks] = useState<WorkflowLock[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(false)
  const [dashboardStats, setDashboardStats] = useState<any>({
    total_critical_alerts: 0,
    total_active_alerts: 0,
    total_active_locks: 0,
    properties_with_good_dscr: 0
  })
  const [propertiesLoading, setPropertiesLoading] = useState(true)
  const [dscrCalculationDetails, setDscrCalculationDetails] = useState<{
    noi?: number
    totalDebtService?: number
    dscr?: number
    period?: string
    isAnnualized?: boolean
  } | null>(null)
  const [showTooltip, setShowTooltip] = useState<string | null>(null)
  const [propertyDSCRHealthy, setPropertyDSCRHealthy] = useState<boolean>(false)

  useEffect(() => {
    fetchProperties()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchAlerts(selectedProperty)
      fetchLocks(selectedProperty)
      fetchAnomalies(selectedProperty)
      fetchPropertyDSCR(selectedProperty)
    } else {
      // Reset stats when no property selected
      setDashboardStats({
        total_critical_alerts: 0,
        total_active_alerts: 0,
        total_active_locks: 0,
        properties_with_good_dscr: 0
      })
      setPropertyDSCRHealthy(false)
    }
  }, [selectedProperty, properties])

  // Update KPIs whenever alerts, locks, or DSCR status changes
  useEffect(() => {
    if (selectedProperty) {
      // Use case-insensitive comparison for status and severity
      const criticalAlerts = alerts.filter(a => {
        const status = (a.status || '').toUpperCase()
        const severity = (a.severity || '').toUpperCase()
        return status === 'ACTIVE' && (severity === 'CRITICAL' || severity === 'URGENT')
      }).length
      
      const activeAlerts = alerts.filter(a => {
        const status = (a.status || '').toUpperCase()
        return status === 'ACTIVE'
      }).length
      
      const activeLocks = locks.filter(l => {
        const status = (l.status || '').toUpperCase()
        return status === 'ACTIVE'
      }).length
      
      setDashboardStats({
        total_critical_alerts: criticalAlerts,
        total_active_alerts: activeAlerts,
        total_active_locks: activeLocks,
        properties_with_good_dscr: propertyDSCRHealthy ? 1 : 0
      })
    }
  }, [alerts, locks, selectedProperty, propertyDSCRHealthy])

  const fetchProperties = async () => {
    try {
      setPropertiesLoading(true)
      // Use propertyService for consistent API handling
      const propertiesList = await propertyService.getAllProperties()
      setProperties(propertiesList)
      if (propertiesList.length > 0) {
        setSelectedProperty(propertiesList[0].id)
      }
    } catch (err) {
      console.error('Failed to fetch properties:', err)
      setProperties([])
    } finally {
      setPropertiesLoading(false)
    }
  }

  const fetchPropertyDSCR = async (propertyId: number) => {
    try {
      // Get the latest period for this property to calculate DSCR
      const periodResponse = await fetch(`${API_BASE_URL}/metrics/summary`, {
        credentials: 'include'
      })
      if (periodResponse.ok) {
        const metricsData = await periodResponse.json()
        const prop = properties.find(p => p.id === propertyId)
        const propertyMetrics = prop ? metricsData.find((m: any) => m.property_code === prop.property_code) : null
        
        if (propertyMetrics?.period_id) {
          const dscrResponse = await fetch(
            `${API_BASE_URL}/risk-alerts/properties/${propertyId}/dscr/calculate?financial_period_id=${propertyMetrics.period_id}`,
            {
              method: 'POST',
              credentials: 'include'
            }
          )
          if (dscrResponse.ok) {
            const dscrData = await dscrResponse.json()
            const hasGoodDSCR = dscrData.success && dscrData.dscr && dscrData.dscr >= 1.25
            setPropertyDSCRHealthy(hasGoodDSCR)
            
            // Store calculation details for tooltip
            if (dscrData.success) {
              setDscrCalculationDetails({
                noi: dscrData.noi,
                totalDebtService: dscrData.total_debt_service,
                dscr: dscrData.dscr,
                period: dscrData.period ? `${dscrData.period.year}-${String(dscrData.period.month).padStart(2, '0')}` : undefined,
                isAnnualized: dscrData.noi && dscrData.noi > 0 && dscrData.total_debt_service && dscrData.noi / dscrData.total_debt_service !== dscrData.dscr
              })
            }
          } else {
            setPropertyDSCRHealthy(false)
            setDscrCalculationDetails(null)
          }
        } else {
          setPropertyDSCRHealthy(false)
          setDscrCalculationDetails(null)
        }
      } else {
        setPropertyDSCRHealthy(false)
        setDscrCalculationDetails(null)
      }
    } catch (err) {
      console.error('Failed to fetch property DSCR:', err)
      setPropertyDSCRHealthy(false)
      setDscrCalculationDetails(null)
    }
  }

  const fetchAlerts = async (propertyId: number) => {
    setLoading(true)
    try {
      // Fetch both active and resolved alerts, but prioritize active ones
      const response = await fetch(`${API_BASE_URL}/risk-alerts/properties/${propertyId}/alerts`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        const allAlerts = data.alerts || []
        
        // Sort: Active alerts first, then resolved, then by date
        const sortedAlerts = allAlerts.sort((a: Alert, b: Alert) => {
          const aStatus = (a.status || '').toUpperCase()
          const bStatus = (b.status || '').toUpperCase()
          
          // Active alerts first
          if (aStatus === 'ACTIVE' && bStatus !== 'ACTIVE') return -1
          if (aStatus !== 'ACTIVE' && bStatus === 'ACTIVE') return 1
          
          // Then by date (newest first)
          const aDate = new Date(a.created_at || a.triggered_at || 0).getTime()
          const bDate = new Date(b.created_at || b.triggered_at || 0).getTime()
          return bDate - aDate
        })
        
        setAlerts(sortedAlerts)
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
      // Use the anomalies endpoint which returns actual anomaly_detections with document info
      const response = await fetch(`${API_BASE_URL}/anomalies?property_id=${propertyId}&limit=100`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setAnomalies(data || [])
      } else {
        console.error('Failed to fetch anomalies:', response.status, response.statusText)
        setAnomalies([])
      }
    } catch (err) {
      console.error('Failed to fetch anomalies:', err)
      setAnomalies([])
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
    const sev = (severity || '').toLowerCase()
    switch (sev) {
      case 'critical':
      case 'urgent':
        return 'error'
      case 'warning':
      case 'high':
        return 'warning'
      case 'medium':
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
      <div className="stats-grid">
        <div 
          className="stat-card stat-error" 
          onClick={() => setActiveTab('alerts')}
          style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <div className="stat-icon">🚨</div>
          <div className="stat-info">
            <div className="stat-value">{dashboardStats.total_critical_alerts || 0}</div>
            <div className="stat-label">Critical Alerts</div>
          </div>
        </div>
        <div 
          className="stat-card stat-warning"
          onClick={() => setActiveTab('alerts')}
          style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <div className="stat-icon">⚠️</div>
          <div className="stat-info">
            <div className="stat-value">{dashboardStats.total_active_alerts || 0}</div>
            <div className="stat-label">Active Alerts</div>
          </div>
        </div>
        <div 
          className="stat-card stat-info"
          onClick={() => setActiveTab('locks')}
          style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <div className="stat-icon">🔒</div>
          <div className="stat-info">
            <div className="stat-value">{dashboardStats.total_active_locks || 0}</div>
            <div className="stat-label">Active Locks</div>
          </div>
        </div>
        <div 
          className="stat-card stat-success"
          onClick={() => setActiveTab('alerts')}
          style={{ cursor: 'pointer', transition: 'transform 0.2s', position: 'relative' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.02)'
            if (selectedProperty && dscrCalculationDetails) {
              setShowTooltip('dscr')
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)'
            setShowTooltip(null)
          }}
        >
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-value">{dashboardStats.properties_with_good_dscr || 0}</div>
            <div className="stat-label">{selectedProperty ? 'Property Health' : 'Healthy Properties'}</div>
          </div>
          {showTooltip === 'dscr' && dscrCalculationDetails && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '8px',
              padding: '12px',
              backgroundColor: '#1a1a1a',
              color: '#fff',
              borderRadius: '8px',
              fontSize: '0.875rem',
              minWidth: '300px',
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              pointerEvents: 'none'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '8px', borderBottom: '1px solid #333', paddingBottom: '4px' }}>
                DSCR Calculation Details
              </div>
              <div style={{ marginBottom: '4px' }}>
                <strong>Formula:</strong> DSCR = NOI / Total Debt Service
              </div>
              <div style={{ marginBottom: '4px' }}>
                <strong>NOI:</strong> ${dscrCalculationDetails.noi?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'N/A'}
                {dscrCalculationDetails.isAnnualized && <span style={{ color: '#ffd700', fontSize: '0.75rem', marginLeft: '4px' }}>(Annualized)</span>}
              </div>
              <div style={{ marginBottom: '4px' }}>
                <strong>Total Debt Service:</strong> ${dscrCalculationDetails.totalDebtService?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'N/A'}
              </div>
              <div style={{ marginBottom: '4px' }}>
                <strong>DSCR:</strong> {dscrCalculationDetails.dscr?.toFixed(4) || 'N/A'}
              </div>
              {dscrCalculationDetails.period && (
                <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#aaa', borderTop: '1px solid #333', paddingTop: '4px' }}>
                  Period: {dscrCalculationDetails.period}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Property Selector */}
      <div className="card">
        <h3 className="card-title">Select Property</h3>
        {propertiesLoading ? (
          <div className="empty-state">
            <p>Loading properties...</p>
          </div>
        ) : properties.length === 0 ? (
          <div className="empty-state">
            <p>⚠️ No properties found. Please create a property first from the Portfolio Hub.</p>
            <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
              Properties are required to view risk alerts and anomalies.
            </p>
          </div>
        ) : (
          <select
            className="select-input"
            value={selectedProperty || ''}
            onChange={(e) => setSelectedProperty(Number(e.target.value))}
          >
            <option value="">Choose a property...</option>
            {properties.map(p => (
              <option key={p.id} value={p.id}>
                {p.property_name}{p.address ? ` - ${p.address}` : ''}
              </option>
            ))}
          </select>
        )}
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
          {loading ? (
            <div className="empty-state">
              <div className="spinner"></div>
              <p>Loading alerts...</p>
            </div>
          ) : alerts.length > 0 ? (
            <div className="alerts-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {alerts.map((alert, idx) => {
                const getAlertExplanation = () => {
                  const alertType = alert.alert_type || 'unknown'
                  const actualValue = alert.actual_value
                  const thresholdValue = alert.threshold_value
                  const fieldName = alert.field_name || 'metric'
                  
                  const explanations: Record<string, string> = {
                    'occupancy_warning': `The occupancy rate is ${actualValue}%, which is below the expected threshold of ${thresholdValue}%. This indicates the property has more vacant units than expected, which could significantly impact revenue and cash flow.`,
                    'covenant_violation': `The ${fieldName.replace('_', ' ')} is ${actualValue}, which exceeds the covenant threshold of ${thresholdValue}. This is a serious violation that may trigger loan default provisions or require immediate corrective action.`,
                    'financial_threshold': `The ${fieldName.replace('_', ' ')} is ${actualValue}, which is below the expected minimum of ${thresholdValue}. This indicates potential financial distress and may require immediate attention to prevent further deterioration.`,
                    'threshold_breach': `The ${fieldName.replace('_', ' ')} value of ${actualValue} has breached the threshold of ${thresholdValue}. This requires investigation to determine if it's a data error or a genuine financial concern.`
                  }
                  
                  return explanations[alertType] || alert.description || `The ${fieldName.replace('_', ' ')} value of ${actualValue} has triggered an alert based on the threshold of ${thresholdValue}.`
                }
                
                return (
                  <div 
                    key={alert.id || idx} 
                    className="alert-card"
                    style={{
                      border: `2px solid ${
                        ['critical', 'urgent'].includes((alert.severity || '').toLowerCase()) ? '#dc3545' :
                        (alert.severity || '').toLowerCase() === 'high' ? '#fd7e14' :
                        (alert.severity || '').toLowerCase() === 'medium' ? '#ffc107' :
                        '#17a2b8'
                      }`,
                      borderRadius: '8px',
                      padding: '1rem',
                      backgroundColor: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                          <span className={`badge badge-${getSeverityColor(alert.severity)}`} style={{ fontSize: '0.75rem' }}>
                            {alert.severity.toUpperCase()}
                          </span>
                          <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                            {alert.alert_type?.replace('_', ' ').toUpperCase() || 'ALERT'}
                          </span>
                          <span className={`badge badge-${(alert.status || '').toUpperCase() === 'ACTIVE' ? 'warning' : 'success'}`} style={{ fontSize: '0.75rem' }}>
                            {(alert.status || '').toUpperCase()}
                          </span>
                        </div>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', fontWeight: '600' }}>
                          📄 {alert.file_name || alert.document_type ? `${alert.document_type?.replace('_', ' ')} Document` : 'Financial Document'}
                        </h4>
                        <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                          <span className="badge badge-info" style={{ marginRight: '0.5rem' }}>
                            {alert.document_type?.replace('_', ' ').toUpperCase() || 'N/A'}
                          </span>
                          {(alert as any).period && (
                            <span className="badge badge-info" style={{ marginRight: '0.5rem', backgroundColor: '#17a2b8' }}>
                              Period: {(alert as any).period}
                            </span>
                          )}
                          {(alert as any).period_year && (alert as any).period_month && !(alert as any).period && (
                            <span className="badge badge-info" style={{ marginRight: '0.5rem', backgroundColor: '#17a2b8' }}>
                              Period: {(alert as any).period_year}-{String((alert as any).period_month).padStart(2, '0')}
                            </span>
                          )}
                          Created: {new Date(alert.created_at || (alert as any).triggered_at || Date.now()).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ 
                      backgroundColor: '#f8f9fa', 
                      padding: '0.75rem', 
                      borderRadius: '4px',
                      marginBottom: '0.75rem'
                    }}>
                      <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#212529' }}>
                        🔍 What's the Issue?
                      </div>
                      <div style={{ fontSize: '0.875rem', lineHeight: '1.5', color: '#495057' }}>
                        {getAlertExplanation()}
                      </div>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.75rem' }}>
                      <div style={{ 
                        backgroundColor: '#fff3cd', 
                        padding: '0.75rem', 
                        borderRadius: '4px',
                        border: '1px solid #ffc107'
                      }}>
                        <div style={{ fontSize: '0.75rem', color: '#856404', marginBottom: '0.25rem', fontWeight: '600' }}>
                          ACTUAL VALUE
                        </div>
                        <div style={{ fontSize: '1.125rem', fontWeight: '600', color: '#856404' }}>
                          {alert.actual_value !== undefined && alert.actual_value !== null
                            ? `${alert.actual_value.toFixed(2)}${alert.threshold_unit === 'percentage' ? '%' : ''}`
                            : 'N/A'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#856404', marginTop: '0.25rem' }}>
                          Field: <strong>{alert.field_name?.replace('_', ' ') || 'N/A'}</strong>
                        </div>
                      </div>
                      
                      <div style={{ 
                        backgroundColor: '#d1ecf1', 
                        padding: '0.75rem', 
                        borderRadius: '4px',
                        border: '1px solid #17a2b8'
                      }}>
                        <div style={{ fontSize: '0.75rem', color: '#0c5460', marginBottom: '0.25rem', fontWeight: '600' }}>
                          THRESHOLD LIMIT
                        </div>
                        <div style={{ fontSize: '1.125rem', fontWeight: '600', color: '#0c5460' }}>
                          {alert.threshold_value !== undefined && alert.threshold_value !== null
                            ? `${alert.threshold_value.toFixed(2)}${alert.threshold_unit === 'percentage' ? '%' : ''}`
                            : 'N/A'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#0c5460', marginTop: '0.25rem' }}>
                          Based on business rules & covenants
                        </div>
                      </div>
                    </div>
                    
                    {(alert.status || '').toUpperCase() === 'ACTIVE' && (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <button
                          className="btn-sm btn-primary"
                          onClick={() => acknowledgeAlert(alert.id)}
                        >
                          Acknowledge Alert
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state">
              <p>✅ No active alerts for this property</p>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
                Risk alerts are automatically generated when financial metrics exceed thresholds or anomalies are detected.
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'locks' && (
        <div className="card">
          <h3 className="card-title">Workflow Locks</h3>
          {loading ? (
            <div className="empty-state">
              <div className="spinner"></div>
              <p>Loading workflow locks...</p>
            </div>
          ) : locks.length > 0 ? (
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
                        <span className={`badge badge-${(lock.status || '').toUpperCase() === 'ACTIVE' ? 'error' : 'success'}`}>
                          {lock.status}
                        </span>
                      </td>
                      <td>
                        {lock.requires_committee_approval ? '✓' : '✗'}
                      </td>
                      <td>{new Date(lock.created_at).toLocaleDateString()}</td>
                      <td>
                        {(lock.status || '').toUpperCase() === 'ACTIVE' && (
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
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
                Workflow locks are automatically created when critical issues require committee approval or manual intervention.
              </p>
              <div style={{ 
                marginTop: '1rem', 
                padding: '0.75rem', 
                backgroundColor: '#e7f3ff',
                borderRadius: '4px',
                border: '1px solid #b3d9ff'
              }}>
                <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#004085', fontSize: '0.875rem' }}>
                  ℹ️ When Workflow Locks Are Created:
                </div>
                <ul style={{ fontSize: '0.875rem', color: '#004085', margin: 0, paddingLeft: '1.5rem' }}>
                  <li>Critical alerts that require committee review</li>
                  <li>DSCR breaches below covenant thresholds</li>
                  <li>Severe covenant violations</li>
                  <li>Manual holds placed by administrators</li>
                  <li>Data quality issues requiring resolution</li>
                </ul>
                <p style={{ fontSize: '0.75rem', color: '#6c757d', marginTop: '0.5rem', marginBottom: 0 }}>
                  Currently, there are no conditions that have triggered workflow locks for this property.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'anomalies' && (
        <div className="card">
          <h3 className="card-title">Detected Anomalies</h3>
          {loading ? (
            <div className="empty-state">
              <div className="spinner"></div>
              <p>Loading anomalies...</p>
            </div>
          ) : anomalies.length > 0 ? (
            <div className="anomalies-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {anomalies.map((anomaly, idx) => {
                const getAnomalyExplanation = () => {
                  const fieldName = anomaly.field_name || 'Unknown field'
                  const actualValue = anomaly.details.field_value || anomaly.value?.toString() || 'N/A'
                  const expectedValue = anomaly.details.expected_value || 'Normal range'
                  const anomalyType = anomaly.type || 'unknown'
                  
                  const explanations: Record<string, string> = {
                    'low_occupancy': `The occupancy rate is ${actualValue}, which is below the expected threshold of ${expectedValue}. This indicates the property has more vacant units than expected, which could impact revenue.`,
                    'low_liquidity': `The current ratio is ${actualValue}, which is below the expected minimum of ${expectedValue}. This indicates the property may have difficulty meeting short-term obligations.`,
                    'extreme_outlier': `The ${fieldName} value of ${actualValue} is an extreme outlier compared to normal ranges. This requires immediate investigation as it may indicate data errors or significant financial issues.`,
                    'high_debt': `The debt-to-equity ratio is ${actualValue}, which is significantly higher than expected. This indicates high financial leverage and potential risk.`,
                    'negative_value': `The ${fieldName} shows a negative value of ${actualValue}, which is unexpected. Negative values may indicate accounting errors or financial distress.`,
                    'missing_data': `Required field ${fieldName} is missing from the document. This may indicate incomplete data extraction or missing information in the source document.`
                  }
                  
                  return explanations[anomalyType] || `The ${fieldName} value of ${actualValue} deviates from the expected ${expectedValue}. This anomaly was detected using statistical analysis.`
                }
                
                const getCalculationDetails = () => {
                  const fieldName = anomaly.field_name || ''
                  
                  // Current Ratio calculation
                  if (fieldName === 'current_ratio' && anomaly.details.total_current_assets !== undefined && anomaly.details.total_current_liabilities !== undefined) {
                    const currentAssets = anomaly.details.total_current_assets
                    const currentLiabilities = anomaly.details.total_current_liabilities
                    const ratio = currentAssets / currentLiabilities
                    return {
                      formula: 'Current Ratio = Current Assets ÷ Current Liabilities',
                      components: [
                        { 
                          label: 'Current Assets (look for "Total Current Assets" line in Balance Sheet)', 
                          value: currentAssets,
                          location: 'Balance Sheet → Assets Section → Total Current Assets'
                        },
                        { 
                          label: 'Current Liabilities (look for "Total Current Liabilities" line in Balance Sheet)', 
                          value: currentLiabilities,
                          location: 'Balance Sheet → Liabilities Section → Total Current Liabilities'
                        },
                        { 
                          label: 'Calculation Result', 
                          value: `${currentAssets.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ÷ ${currentLiabilities.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} = ${ratio.toFixed(4)}`,
                          isResult: true
                        }
                      ]
                    }
                  }
                  
                  // Debt-to-Equity Ratio calculation
                  if (fieldName === 'debt_to_equity_ratio' && anomaly.details.total_liabilities !== undefined && anomaly.details.total_equity !== undefined) {
                    const totalLiabilities = anomaly.details.total_liabilities
                    const totalEquity = anomaly.details.total_equity
                    const ratio = totalLiabilities / totalEquity
                    return {
                      formula: 'Debt-to-Equity Ratio = Total Liabilities ÷ Total Equity',
                      components: [
                        { 
                          label: 'Total Liabilities (look for "Total Liabilities" line in Balance Sheet)', 
                          value: totalLiabilities,
                          location: 'Balance Sheet → Liabilities Section → Total Liabilities'
                        },
                        { 
                          label: 'Total Equity (look for "Total Equity" or "Total Capital" line in Balance Sheet)', 
                          value: totalEquity,
                          location: 'Balance Sheet → Equity/Capital Section → Total Equity'
                        },
                        { 
                          label: 'Calculation Result', 
                          value: `${totalLiabilities.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ÷ ${totalEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} = ${ratio.toFixed(4)}`,
                          isResult: true
                        }
                      ]
                    }
                  }
                  
                  // Occupancy Rate calculation
                  if (fieldName === 'occupancy_rate' && anomaly.details.total_units !== undefined && anomaly.details.occupied_units !== undefined) {
                    const occupied = anomaly.details.occupied_units
                    const total = anomaly.details.total_units
                    const rate = (occupied / total) * 100
                    return {
                      formula: 'Occupancy Rate = (Occupied Units ÷ Total Units) × 100%',
                      components: [
                        { 
                          label: 'Occupied Units (count of occupied units in Rent Roll)', 
                          value: occupied,
                          location: 'Rent Roll → Count units with status "Occupied"'
                        },
                        { 
                          label: 'Total Units (total number of units in Rent Roll)', 
                          value: total,
                          location: 'Rent Roll → Total number of units listed'
                        },
                        { 
                          label: 'Calculation Result', 
                          value: `(${occupied} ÷ ${total}) × 100% = ${rate.toFixed(2)}%`,
                          isResult: true
                        }
                      ]
                    }
                  }
                  
                  return null
                }
                
                const calculationDetails = getCalculationDetails()
                
                return (
                  <div 
                    key={anomaly.record_id || idx} 
                    className="anomaly-card"
                    style={{
                      border: `2px solid ${
                        anomaly.severity === 'critical' ? '#dc3545' :
                        anomaly.severity === 'high' ? '#fd7e14' :
                        anomaly.severity === 'medium' ? '#ffc107' :
                        '#17a2b8'
                      }`,
                      borderRadius: '8px',
                      padding: '1rem',
                      backgroundColor: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                          <span className={`badge badge-${getSeverityColor(anomaly.severity)}`} style={{ fontSize: '0.75rem' }}>
                            {anomaly.severity.toUpperCase()}
                          </span>
                          <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>
                            {anomaly.type?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                          </span>
                        </div>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', fontWeight: '600' }}>
                          📄 {anomaly.details.file_name || 'Unknown File'}
                        </h4>
                        <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                          <span className="badge badge-info" style={{ marginRight: '0.5rem' }}>
                            {anomaly.details.document_type?.replace('_', ' ').toUpperCase() || 'N/A'}
                          </span>
                          Period: {anomaly.details.period || 'N/A'}
                          {anomaly.details.upload_date && (
                            <> • Uploaded: {new Date(anomaly.details.upload_date).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ 
                      backgroundColor: '#f8f9fa', 
                      padding: '0.75rem', 
                      borderRadius: '4px',
                      marginBottom: '0.75rem'
                    }}>
                      <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#212529' }}>
                        🔍 What's the Issue?
                      </div>
                      <div style={{ fontSize: '0.875rem', lineHeight: '1.5', color: '#495057', marginBottom: '0.75rem' }}>
                        {getAnomalyExplanation()}
                      </div>
                      {calculationDetails && (
                        <div style={{ 
                          marginTop: '0.75rem', 
                          padding: '0.75rem', 
                          backgroundColor: '#e7f3ff',
                          borderRadius: '4px',
                          border: '1px solid #b3d9ff'
                        }}>
                          <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#004085', fontSize: '0.875rem' }}>
                            📊 How This Metric is Calculated:
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#004085', marginBottom: '0.5rem', fontFamily: 'monospace' }}>
                            <strong>{calculationDetails.formula}</strong>
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#004085' }}>
                            <div style={{ marginBottom: '0.5rem', fontWeight: '600' }}>
                              📍 Where to find these values in "{anomaly.details.file_name}":
                            </div>
                            {calculationDetails.components.map((comp, idx) => (
                              <div key={idx} style={{ 
                                marginLeft: '0.5rem', 
                                marginBottom: '0.5rem',
                                padding: '0.5rem',
                                backgroundColor: comp.isResult ? '#fff' : '#f0f8ff',
                                borderRadius: '4px',
                                border: comp.isResult ? '2px solid #004085' : '1px solid #b3d9ff'
                              }}>
                                <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                                  {comp.isResult ? '=' : `${idx + 1}.`} {comp.label}
                                </div>
                                {!comp.isResult && (
                                  <>
                                    <div style={{ fontSize: '1rem', fontWeight: '700', color: '#004085', margin: '0.25rem 0' }}>
                                      ${comp.value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: '#6c757d', fontStyle: 'italic' }}>
                                      Location: {comp.location}
                                    </div>
                                  </>
                                )}
                                {comp.isResult && (
                                  <div style={{ fontSize: '1rem', fontWeight: '700', color: '#004085' }}>
                                    {comp.value}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {!calculationDetails && (
                        <div style={{ 
                          marginTop: '0.75rem', 
                          padding: '0.5rem', 
                          backgroundColor: '#fff3cd',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          color: '#856404'
                        }}>
                          ⚠️ Note: This is a calculated metric derived from multiple line items in the {anomaly.details.document_type?.replace('_', ' ') || 'document'}. 
                          The specific calculation details are not available in the anomaly record.
                        </div>
                      )}
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.75rem' }}>
                      <div style={{ 
                        backgroundColor: '#fff3cd', 
                        padding: '0.75rem', 
                        borderRadius: '4px',
                        border: '1px solid #ffc107'
                      }}>
                        <div style={{ fontSize: '0.75rem', color: '#856404', marginBottom: '0.25rem', fontWeight: '600' }}>
                          ACTUAL VALUE
                        </div>
                        <div style={{ fontSize: '1.125rem', fontWeight: '600', color: '#856404' }}>
                          {anomaly.details.field_value || (anomaly.value !== undefined && anomaly.value !== null
                            ? typeof anomaly.value === 'number'
                              ? anomaly.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                              : anomaly.value
                            : 'N/A')}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#856404', marginTop: '0.25rem' }}>
                          Field: <strong>{anomaly.field_name || 'N/A'}</strong>
                        </div>
                      </div>
                      
                      <div style={{ 
                        backgroundColor: '#d1ecf1', 
                        padding: '0.75rem', 
                        borderRadius: '4px',
                        border: '1px solid #17a2b8'
                      }}>
                        <div style={{ fontSize: '0.75rem', color: '#0c5460', marginBottom: '0.25rem', fontWeight: '600' }}>
                          EXPECTED VALUE
                        </div>
                        <div style={{ fontSize: '1.125rem', fontWeight: '600', color: '#0c5460' }}>
                          {anomaly.details.expected_value || 'Normal range'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#0c5460', marginTop: '0.25rem' }}>
                          Based on business rules & historical data
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ 
                      display: 'flex', 
                      gap: '1rem', 
                      fontSize: '0.875rem',
                      color: '#6b7280',
                      flexWrap: 'wrap'
                    }}>
                      {anomaly.details.z_score && (
                        <div>
                          <strong>Z-Score:</strong> {anomaly.details.z_score.toFixed(2)} 
                          <span style={{ fontSize: '0.75rem', marginLeft: '0.25rem' }}>
                            ({anomaly.details.z_score > 3 ? 'Extreme' : anomaly.details.z_score > 2 ? 'Significant' : 'Moderate'} deviation)
                          </span>
                        </div>
                      )}
                      {anomaly.details.percentage_change && (
                        <div>
                          <strong>Change:</strong> {anomaly.details.percentage_change > 0 ? '+' : ''}{anomaly.details.percentage_change.toFixed(1)}%
                        </div>
                      )}
                      {anomaly.details.confidence && (
                        <div>
                          <strong>Detection Confidence:</strong> {(anomaly.details.confidence * 100).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state">
              <p>✅ No anomalies detected for this property</p>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
                Anomalies are automatically detected when financial data deviates from expected patterns or historical baselines.
              </p>
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
