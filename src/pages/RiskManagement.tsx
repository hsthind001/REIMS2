import { useState, useEffect } from 'react'
import '../App.css'
import { propertyService } from '../lib/property'
import {
  getAllAccountsWithThresholds,
  getDefaultThreshold,
  setDefaultThreshold,
  saveThreshold
} from '../lib/anomalyThresholds'
import { AnomalyFieldViewer } from '../components/AnomalyFieldViewer'

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1'

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
  const [activeTab, setActiveTab] = useState<'alerts' | 'locks' | 'anomalies' | 'thresholds'>('alerts')
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [locks, setLocks] = useState<WorkflowLock[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(false)
  const [accountsWithThresholds, setAccountsWithThresholds] = useState<any[]>([])
  const [defaultThreshold, setDefaultThreshold] = useState<number>(0.01) // 1% as decimal
  const [editingThreshold, setEditingThreshold] = useState<string | null>(null)
  const [editingValue, setEditingValue] = useState<number | null>(null)
  const [thresholdsLoading, setThresholdsLoading] = useState(false)
  const [selectedDocumentType, setSelectedDocumentType] = useState<string>('all')
  const [selectedAnomalyDocumentType, setSelectedAnomalyDocumentType] = useState<string>('all')
  const [dashboardStats, setDashboardStats] = useState<any>({
    total_critical_alerts: 0,
    total_active_alerts: 0,
    total_active_locks: 0,
    properties_with_good_dscr: 0
  })
  const [propertiesLoading, setPropertiesLoading] = useState(true)
  // Side panel state for field viewer
  const [fieldViewerOpen, setFieldViewerOpen] = useState(false)
  const [selectedAnomalyForViewer, setSelectedAnomalyForViewer] = useState<Anomaly | null>(null)
  const [fieldViewerType, setFieldViewerType] = useState<'actual' | 'expected'>('actual')
  const [dscrCalculationDetails, setDscrCalculationDetails] = useState<{
    noi?: number
    totalDebtService?: number
    dscr?: number
    period?: string
    isAnnualized?: boolean
  } | null>(null)
  const [showTooltip, setShowTooltip] = useState<string | null>(null)
  const [propertyDSCRHealthy, setPropertyDSCRHealthy] = useState<boolean>(false)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null)
  const [emailAddress, setEmailAddress] = useState('')
  const [emailError, setEmailError] = useState('')

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

  useEffect(() => {
    if (selectedProperty && activeTab === 'anomalies') {
      fetchAnomalies(selectedProperty)
    }
  }, [selectedAnomalyDocumentType, selectedProperty, activeTab])

  useEffect(() => {
    if (activeTab === 'thresholds') {
      fetchThresholds()
    }
  }, [activeTab, selectedDocumentType])

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
      // Build query parameters
      const params = new URLSearchParams({
        property_id: propertyId.toString(),
        limit: '100'
      })
      
      // Add document_type filter if not 'all'
      if (selectedAnomalyDocumentType && selectedAnomalyDocumentType !== 'all') {
        params.append('document_type', selectedAnomalyDocumentType)
      }
      
      // Use the anomalies endpoint which returns actual anomaly_detections with document info
      const response = await fetch(`${API_BASE_URL}/anomalies?${params.toString()}`, {
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

  const fetchThresholds = async () => {
    setThresholdsLoading(true)
    try {
      const documentType = selectedDocumentType === 'all' ? undefined : selectedDocumentType
      const [accounts, defaultThresh] = await Promise.all([
        getAllAccountsWithThresholds(documentType),
        getDefaultThreshold()
      ])
      setAccountsWithThresholds(accounts)
      setDefaultThreshold(defaultThresh.default_threshold)
    } catch (err) {
      console.error('Failed to fetch thresholds:', err)
      setAccountsWithThresholds([])
    } finally {
      setThresholdsLoading(false)
    }
  }

  const handleSaveThreshold = async (accountCode: string, accountName: string, thresholdValue: number) => {
    try {
      await saveThreshold(accountCode, accountName, thresholdValue, true)
      setEditingThreshold(null)
      setEditingValue(null)
      await fetchThresholds() // Refresh the list
    } catch (err: any) {
      console.error('Failed to save threshold:', err)
      alert(`Failed to save threshold: ${err.message || 'Unknown error'}`)
    }
  }

  const handleSaveDefaultThreshold = async (thresholdValue: number) => {
    try {
      await setDefaultThreshold(thresholdValue)
      setDefaultThreshold(thresholdValue)
      await fetchThresholds() // Refresh the list to update default values
    } catch (err: any) {
      console.error('Failed to save default threshold:', err)
      alert(`Failed to save default threshold: ${err.message || 'Unknown error'}`)
    }
  }

  const acknowledgeAlert = async (alertId: number) => {
    // Show email modal instead of directly acknowledging
    setSelectedAlertId(alertId)
    setShowEmailModal(true)
    setEmailAddress('')
    setEmailError('')
  }

  const handleEmailSubmit = async () => {
    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailAddress || !emailRegex.test(emailAddress)) {
      setEmailError('Please enter a valid email address')
      return
    }

    if (!selectedAlertId) return

    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${selectedAlertId}/acknowledge`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          acknowledged_by: 1, 
          email: emailAddress,
          notes: 'Acknowledged from UI' 
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // Always acknowledge the alert even if email fails
        setShowEmailModal(false)
        setSelectedAlertId(null)
        setEmailAddress('')
        setEmailError('')
        if (selectedProperty) {
          fetchAlerts(selectedProperty)
        }
        
        // Show success message based on email status
        if (data.email_sent) {
          if (data.development_mode) {
            alert('✅ Alert acknowledged! Email logged (SMTP server not configured - check backend logs for email content).')
          } else {
            alert('✅ Alert acknowledged and email sent successfully!')
          }
        } else if (data.email_error) {
          // Alert was acknowledged but email failed - still show success for acknowledgment
          alert(`✅ Alert acknowledged successfully!\n\n⚠️ Note: Email could not be sent: ${data.email_error}\n\nYou can check the alert details in the system.`)
        } else {
          alert('✅ Alert acknowledged successfully!')
        }
      } else {
        // Only show error if the acknowledgment itself failed
        const errorData = await response.json().catch(() => ({ detail: 'Failed to acknowledge alert' }))
        const errorMessage = errorData.detail || 'Failed to acknowledge alert. Please try again.'
        setEmailError(errorMessage)
        console.error('Acknowledge alert error:', errorData)
      }
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
      setEmailError('Failed to send email. Please try again.')
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
      <div className="tabs" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <button
          className={`tab ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          🚨 Risk Alerts ({alerts.length})
        </button>
        <button
          onClick={() => {
            window.location.hash = '#alert-rules';
          }}
          style={{
            padding: '0.5rem 1rem',
            background: '#28a745',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '600',
            marginLeft: 'auto'
          }}
        >
          ⚙️ Manage Alert Rules
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
        <button
          className={`tab ${activeTab === 'thresholds' ? 'active' : ''}`}
          onClick={() => setActiveTab('thresholds')}
        >
          ⚙️ Value Setup
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 className="card-title" style={{ margin: 0 }}>Detected Anomalies</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>
                Filter by Document Type:
              </label>
              <select
                value={selectedAnomalyDocumentType}
                onChange={(e) => setSelectedAnomalyDocumentType(e.target.value)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  minWidth: '200px'
                }}
              >
                <option value="all">All Document Types</option>
                <option value="income_statement">Income Statement</option>
                <option value="balance_sheet">Balance Sheet</option>
                <option value="cash_flow">Cash Flow Statement</option>
                <option value="rent_roll">Rent Roll</option>
              </select>
            </div>
          </div>
          {loading ? (
            <div className="empty-state">
              <div className="spinner"></div>
              <p>Loading anomalies...</p>
            </div>
          ) : anomalies.length > 0 ? (
            <div className="anomalies-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {anomalies.map((anomaly, idx) => {
                const getAnomalyExplanation = () => {
                  const accountName = anomaly.details.account_name || anomaly.field_name || 'Unknown field'
                  const fieldCode = anomaly.field_name || 'Unknown field'
                  const actualValue = anomaly.details.field_value || anomaly.value?.toString() || 'N/A'
                  const expectedValue = anomaly.details.expected_value || 'Normal range'
                  const anomalyType = anomaly.type || 'unknown'
                  
                  const explanations: Record<string, string> = {
                    'low_occupancy': `The occupancy rate is ${actualValue}, which is below the expected threshold of ${expectedValue}. This indicates the property has more vacant units than expected, which could impact revenue.`,
                    'low_liquidity': `The current ratio is ${actualValue}, which is below the expected minimum of ${expectedValue}. This indicates the property may have difficulty meeting short-term obligations.`,
                    'extreme_outlier': `The ${accountName} (${fieldCode}) value of ${actualValue} is an extreme outlier compared to normal ranges. This requires immediate investigation as it may indicate data errors or significant financial issues.`,
                    'high_debt': `The debt-to-equity ratio is ${actualValue}, which is significantly higher than expected. This indicates high financial leverage and potential risk.`,
                    'negative_value': `The ${accountName} (${fieldCode}) shows a negative value of ${actualValue}, which is unexpected. Negative values may indicate accounting errors or financial distress.`,
                    'missing_data': `Required field ${accountName} (${fieldCode}) is missing from the document. This may indicate incomplete data extraction or missing information in the source document.`
                  }
                  
                  return explanations[anomalyType] || `The ${accountName} (${fieldCode}) value of ${actualValue} deviates from the expected ${expectedValue}. This anomaly was detected using statistical analysis.`
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
                          {(() => {
                            const accountName = anomaly.details.account_name || anomaly.field_name || 'N/A'
                            // Get year from period_year field, or parse from period string (format: "YYYY/MM")
                            // Fallback: extract from message field which contains "PROPERTY_CODE (YYYY/MM): ..."
                            let year = null
                            if (anomaly.details?.period_year) {
                              year = String(anomaly.details.period_year)
                            } else if (anomaly.details?.period) {
                              const periodParts = String(anomaly.details.period).split('/')
                              year = periodParts[0] || null
                            } else if (anomaly.message) {
                              // Extract year from message format: "PROPERTY_CODE (YYYY/MM): ..."
                              const match = anomaly.message.match(/\((\d{4})\/\d{2}\)/)
                              if (match) {
                                year = match[1]
                              }
                            }
                            return year ? `${accountName} (${year})` : accountName
                          })()}
                        </div>
                        <div 
                          style={{ 
                            fontSize: '1.125rem', 
                            fontWeight: '600', 
                            color: '#856404',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            textDecorationStyle: 'dotted'
                          }}
                          onClick={() => {
                            if (!anomaly.record_id) {
                              alert(`Cannot open PDF: Anomaly record ID is missing. Please contact support.`)
                              return
                            }
                            setSelectedAnomalyForViewer(anomaly)
                            setFieldViewerType('actual')
                            setFieldViewerOpen(true)
                          }}
                          title="Click to view this value in the PDF"
                        >
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
                          {(() => {
                            const accountName = anomaly.details.account_name || anomaly.field_name || 'N/A'
                            // Get year from period_year field, or parse from period string (format: "YYYY/MM")
                            // Use the same year as the first box (current file's year)
                            let year = null
                            if (anomaly.details?.period_year) {
                              year = String(anomaly.details.period_year)
                            } else if (anomaly.details?.period) {
                              const periodParts = String(anomaly.details.period).split('/')
                              year = periodParts[0] || null
                            }
                            return year ? `${accountName} (${year})` : accountName
                          })()}
                        </div>
                        <div 
                          style={{ 
                            fontSize: '1.125rem', 
                            fontWeight: '600', 
                            color: '#0c5460',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            textDecorationStyle: 'dotted'
                          }}
                          onClick={() => {
                            if (!anomaly.record_id) {
                              alert(`Cannot open PDF: Anomaly record ID is missing. Please contact support.`)
                              return
                            }
                            setSelectedAnomalyForViewer(anomaly)
                            setFieldViewerType('expected')
                            setFieldViewerOpen(true)
                          }}
                          title="Click to view expected value location in the PDF"
                        >
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
                      {(() => {
                        // Calculate percentage change from actual values if available, otherwise use stored value
                        let pctChange = anomaly.details.percentage_change;
                        
                        // Recalculate from field_value and expected_value to ensure correct sign
                        if (anomaly.details.field_value && anomaly.details.expected_value) {
                          try {
                            const currentVal = parseFloat(String(anomaly.details.field_value));
                            const expectedVal = parseFloat(String(anomaly.details.expected_value));
                            
                            if (!isNaN(currentVal) && !isNaN(expectedVal) && expectedVal !== 0) {
                              // Calculate: (current - expected) / expected * 100
                              // Positive = increase, Negative = decrease
                              pctChange = ((currentVal - expectedVal) / expectedVal) * 100;
                            }
                          } catch (e) {
                            // Fall back to stored value if calculation fails
                          }
                        }
                        
                        return pctChange !== null && pctChange !== undefined ? (
                          <div>
                            <strong>Change:</strong> {pctChange > 0 ? '+' : ''}{pctChange.toFixed(1)}%
                          </div>
                        ) : null;
                      })()}
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

      {activeTab === 'thresholds' && (
        <div className="card">
          <h3 className="card-title">Value Setup - Anomaly Thresholds</h3>
          <p style={{ marginBottom: '1.5rem', color: '#6b7280', fontSize: '0.875rem' }}>
            Configure percentage thresholds for each account code. If the percentage change in value exceeds the threshold, 
            the field will appear in anomalies. Fields without custom thresholds use the global default.
          </p>

          {/* Document Type Filter */}
          <div style={{ 
            marginBottom: '1.5rem', 
            padding: '1rem', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px',
            border: '1px solid #e5e7eb'
          }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
              Filter by Document Type
            </label>
            <select
              value={selectedDocumentType}
              onChange={(e) => setSelectedDocumentType(e.target.value)}
              style={{
                padding: '0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                width: '250px',
                fontSize: '0.875rem',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}
            >
              <option value="all">All Document Types</option>
              <option value="income_statement">Income Statement</option>
              <option value="balance_sheet">Balance Sheet</option>
              <option value="cash_flow">Cash Flow Statement</option>
              <option value="rent_roll">Rent Roll</option>
            </select>
            <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem' }}>
              Showing {accountsWithThresholds.length} account{accountsWithThresholds.length !== 1 ? 's' : ''} 
              {selectedDocumentType !== 'all' && ` for ${selectedDocumentType.replace('_', ' ')}`}
            </p>
          </div>

          {/* Global Default Threshold */}
          <div style={{ 
            marginBottom: '2rem', 
            padding: '1rem', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px',
            border: '1px solid #e5e7eb'
          }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
              Global Default Threshold
            </label>
            <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.75rem' }}>
              This percentage threshold will be used for all account codes that don't have a custom threshold set.
              Enter as a percentage (e.g., 1 for 1%).
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="number"
                value={defaultThreshold * 100} // Display as percentage
                onChange={(e) => setDefaultThreshold((parseFloat(e.target.value) || 0) / 100)} // Convert to decimal
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  width: '200px',
                  fontSize: '0.875rem'
                }}
                step="0.1"
                min="0"
              />
              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>%</span>
              <button
                onClick={() => handleSaveDefaultThreshold(defaultThreshold)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}
              >
                Save Default
              </button>
            </div>
          </div>

          {/* Thresholds Table */}
          {thresholdsLoading ? (
            <div className="empty-state">
              <div className="spinner"></div>
              <p>Loading thresholds...</p>
            </div>
          ) : accountsWithThresholds.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#374151' }}>Account Code</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#374151' }}>Account Name</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#374151' }}>Threshold Value (%)</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#374151' }}>Status</th>
                    <th style={{ padding: '0.75rem', textAlign: 'center', fontWeight: '600', color: '#374151' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {accountsWithThresholds.map((account) => {
                    const isEditing = editingThreshold === account.account_code
                    // Convert decimal threshold to percentage for display
                    const thresholdDecimal = isEditing 
                      ? (editingValue !== null ? editingValue : (account.threshold_value || account.default_threshold))
                      : (account.threshold_value || account.default_threshold)
                    const displayValue = thresholdDecimal * 100 // Convert to percentage for display
                    
                    return (
                      <tr 
                        key={account.account_code}
                        style={{ 
                          borderBottom: '1px solid #e5e7eb',
                          backgroundColor: isEditing ? '#fef3c7' : 'white'
                        }}
                      >
                        <td style={{ padding: '0.75rem', fontSize: '0.875rem', fontFamily: 'monospace' }}>
                          {account.account_code}
                        </td>
                        <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                          {account.account_name}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          {isEditing ? (
                            <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                              <input
                                type="number"
                                value={displayValue}
                                onChange={(e) => setEditingValue((parseFloat(e.target.value) || 0) / 100)} // Convert to decimal
                                style={{
                                  padding: '0.5rem',
                                  border: '1px solid #3b82f6',
                                  borderRadius: '4px',
                                  width: '120px',
                                  fontSize: '0.875rem'
                                }}
                                step="0.1"
                                min="0"
                                autoFocus
                              />
                              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>%</span>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.875rem', color: account.is_custom ? '#374151' : '#6b7280' }}>
                              {displayValue.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%
                              {!account.is_custom && (
                                <span style={{ fontSize: '0.75rem', color: '#9ca3af', marginLeft: '0.5rem' }}>
                                  (default)
                                </span>
                              )}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            fontSize: '0.75rem',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            backgroundColor: account.is_custom ? '#dbeafe' : '#f3f4f6',
                            color: account.is_custom ? '#1e40af' : '#6b7280',
                            fontWeight: '500'
                          }}>
                            {account.is_custom ? 'Custom' : 'Default'}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                          {isEditing ? (
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                              <button
                                onClick={() => handleSaveThreshold(account.account_code, account.account_name, editingValue !== null ? editingValue : (account.threshold_value || account.default_threshold))}
                                style={{
                                  padding: '0.375rem 0.75rem',
                                  backgroundColor: '#10b981',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '0.75rem',
                                  fontWeight: '500'
                                }}
                              >
                                Save
                              </button>
                              <button
                                onClick={() => {
                                  setEditingThreshold(null)
                                  setEditingValue(null)
                                }}
                                style={{
                                  padding: '0.375rem 0.75rem',
                                  backgroundColor: '#6b7280',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '0.75rem',
                                  fontWeight: '500'
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setEditingThreshold(account.account_code)
                                setEditingValue(account.threshold_value || account.default_threshold)
                              }}
                              style={{
                                padding: '0.375rem 0.75rem',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                                fontWeight: '500'
                              }}
                            >
                              {account.is_custom ? 'Edit' : 'Set Custom'}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <p>No accounts found. Please ensure chart of accounts is populated.</p>
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

      {/* Email Modal */}
      {showEmailModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            maxWidth: '500px',
            width: '90%',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Enter Email Address</h3>
            <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
              Please provide an email address where you would like to receive the alert details.
            </p>
            <input
              type="email"
              value={emailAddress}
              onChange={(e) => {
                setEmailAddress(e.target.value)
                setEmailError('')
              }}
              placeholder="your.email@example.com"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: `1px solid ${emailError ? '#dc3545' : '#d1d5db'}`,
                borderRadius: '4px',
                fontSize: '1rem',
                marginBottom: '0.5rem'
              }}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleEmailSubmit()
                }
              }}
            />
            {emailError && (
              <div style={{ color: '#dc3545', fontSize: '0.875rem', marginBottom: '1rem' }}>
                {emailError}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowEmailModal(false)
                  setSelectedAlertId(null)
                  setEmailAddress('')
                  setEmailError('')
                }}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleEmailSubmit}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Send Email & Acknowledge
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Anomaly Field Viewer Side Panel */}
      {selectedAnomalyForViewer && (
        <AnomalyFieldViewer
          anomaly={selectedAnomalyForViewer}
          fieldType={fieldViewerType}
          isOpen={fieldViewerOpen}
          onClose={() => {
            setFieldViewerOpen(false)
            setSelectedAnomalyForViewer(null)
          }}
        />
      )}
    </div>
  )
}
