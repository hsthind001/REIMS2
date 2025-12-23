/**
 * Risk Management Dashboard - World-Class Redesign
 * 
 * Comprehensive risk management interface with:
 * - Executive summary and KPIs
 * - Unified risk workbench (anomalies, alerts, locks)
 * - Property-specific risk views
 * - Batch operations and automation
 * - Real-time updates and analytics
 * - Advanced filtering and search
 * - Export capabilities
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import '../App.css'
import { 
  Shield, AlertTriangle, Lock, TrendingUp, TrendingDown, 
  RefreshCw, Filter, Search, Download, Settings, BarChart3,
  CheckCircle, XCircle, Clock, Activity, Zap, Eye, EyeOff
} from 'lucide-react'
import { propertyService } from '../lib/property'
import { anomaliesService } from '../lib/anomalies'
import { workflowLockService, type WorkflowLock } from '../lib/workflowLocks'
import { batchReprocessingService, type BatchReprocessingJob } from '../lib/batchReprocessing'
import RiskWorkbenchTable, { RiskItem } from '../components/risk-workbench/RiskWorkbenchTable'
import { BatchReprocessingForm } from '../components/anomalies/BatchReprocessingForm'
import { ExportButton } from '../components/ExportButton'
import { useAuth } from '../components/AuthContext'
import AnomalyDetail from '../components/anomalies/AnomalyDetail'
import AlertDetailView from '../components/alerts/AlertDetailView'
import { AlertService } from '../lib/alerts'

const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1` 
  : 'http://localhost:8000/api/v1'

interface DashboardStats {
  total_critical_alerts: number
  total_active_alerts: number
  total_active_locks: number
  total_anomalies: number
  properties_at_risk: number
  total_properties: number
  avg_resolution_time_hours: number
  sla_compliance_rate: number
}

interface Property {
  id: number
  property_code: string
  property_name: string
  property_type?: string
}

type ViewMode = 'unified' | 'anomalies' | 'alerts' | 'locks' | 'analytics'
type DetailView = 'anomaly' | 'alert' | null

export default function RiskManagement() {
  const { user } = useAuth()
  
  // Core state
  const [viewMode, setViewMode] = useState<ViewMode>('unified')
  const [properties, setProperties] = useState<Property[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [dashboardStats, setDashboardStats] = useState<DashboardStats>({
    total_critical_alerts: 0,
    total_active_alerts: 0,
    total_active_locks: 0,
    total_anomalies: 0,
    properties_at_risk: 0,
    total_properties: 0,
    avg_resolution_time_hours: 0,
    sla_compliance_rate: 0
  })
  
  // Risk items
  const [riskItems, setRiskItems] = useState<RiskItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Filters
  const [filters, setFilters] = useState({
    propertyId: null as number | null,
    documentType: '',
    severity: '',
    status: '',
    searchQuery: ''
  })
  
  // Detail views
  const [selectedDetail, setSelectedDetail] = useState<{ type: DetailView; id: number } | null>(null)
  const [showBatchForm, setShowBatchForm] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(30000) // 30 seconds

  // Load properties on mount
  useEffect(() => {
    fetchProperties()
  }, [])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return
    
    const interval = setInterval(() => {
      if (viewMode === 'unified') {
        loadUnifiedRiskItems()
      } else {
        loadDashboardStats()
      }
    }, refreshInterval)
    
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, viewMode, filters])

  // Load data when filters or view changes
  useEffect(() => {
    loadDashboardStats()
    if (viewMode === 'unified') {
      loadUnifiedRiskItems()
    }
  }, [selectedProperty, viewMode, filters.propertyId])

  const fetchProperties = async () => {
    try {
      const props = await propertyService.getAllProperties()
      setProperties(props)
      setDashboardStats(prev => ({ ...prev, total_properties: props.length }))
    } catch (err: any) {
      console.error('Failed to fetch properties:', err)
    }
  }

  const loadDashboardStats = async () => {
    try {
      // Load alerts summary
      const alertsResponse = await fetch(
        `${API_BASE_URL}/risk-alerts/dashboard/summary${selectedProperty ? `?property_id=${selectedProperty}` : ''}`,
        { credentials: 'include' }
      )
      
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json()
        setDashboardStats(prev => ({
          ...prev,
          total_critical_alerts: alertsData.critical_alerts || 0,
          total_active_alerts: alertsData.active_alerts || 0,
          properties_at_risk: alertsData.properties_at_risk || 0,
          avg_resolution_time_hours: alertsData.avg_resolution_time_hours || 0,
          sla_compliance_rate: alertsData.sla_compliance_rate || 0
        }))
      }

      // Load locks count
      if (selectedProperty) {
        const locksResult = await workflowLockService.getPropertyLocks(selectedProperty, 'ACTIVE')
        setDashboardStats(prev => ({
          ...prev,
          total_active_locks: locksResult.total || 0
        }))
      } else {
        // Get all active locks
        const statsResult = await workflowLockService.getStatistics()
        setDashboardStats(prev => ({
          ...prev,
          total_active_locks: statsResult.statistics?.active_locks || 0
        }))
      }

      // Load anomalies count
      const anomaliesResponse = await fetch(
        `${API_BASE_URL}/anomalies?${selectedProperty ? `property_id=${selectedProperty}&` : ''}limit=1`,
        { credentials: 'include' }
      )
      
      if (anomaliesResponse.ok) {
        // We'll get total from unified endpoint
        const anomaliesData = await anomaliesResponse.json()
        // For now, we'll update from unified load
      }
    } catch (err: any) {
      console.error('Failed to load dashboard stats:', err)
    }
  }

  const loadUnifiedRiskItems = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const params = new URLSearchParams()
      if (filters.propertyId) params.append('property_id', filters.propertyId.toString())
      if (filters.documentType) params.append('document_type', filters.documentType)
      if (filters.severity) params.append('severity', filters.severity)
      params.append('page', '1')
      params.append('page_size', '1000')
      params.append('sort_by', 'created_at')
      params.append('sort_order', 'desc')

      const response = await fetch(`${API_BASE_URL}/risk-workbench/unified?${params.toString()}`, {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Get property names map for better display
      const propertyMap = new Map(properties.map(p => [p.property_code, p.property_name]))
      
      // Transform to RiskItem format
      const transformedItems: RiskItem[] = data.items.map((item: any) => {
        const propertyCode = item.property || item.property_code
        const propertyName = propertyMap.get(propertyCode) || propertyCode || 'Unknown Property'
        
        return {
          id: item.id,
          type: item.type,
          severity: item.severity?.toLowerCase() || 'medium',
          property_id: filters.propertyId || 0,
          property_name: propertyName,
          age_days: item.age_days || Math.floor((item.age_seconds || 0) / 86400),
          impact_amount: item.impact ? parseFloat(item.impact) : undefined,
          status: item.status || 'active',
          assignee: item.assignee,
          due_date: item.due_date,
          title: item.title || `${item.type} - ${propertyName}`,
          description: item.description,
          created_at: item.created_at || new Date().toISOString(),
          updated_at: item.updated_at || new Date().toISOString(),
          metadata: {
            ...(item.metadata || {}),
            property_code: propertyCode
          }
        }
      })

      setRiskItems(transformedItems)
      
      // Update stats
      setDashboardStats(prev => ({
        ...prev,
        total_anomalies: transformedItems.filter(i => i.type === 'anomaly').length,
        total_active_alerts: transformedItems.filter(i => i.type === 'alert' && i.status === 'active').length
      }))
    } catch (err: any) {
      setError(err.message || 'Failed to load risk items')
      console.error('Error loading risk items:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = useCallback((item: RiskItem) => {
    if (item.type === 'anomaly') {
      setSelectedDetail({ type: 'anomaly', id: item.id })
    } else if (item.type === 'alert') {
      setSelectedDetail({ type: 'alert', id: item.id })
    }
  }, [])

  const handleAcknowledge = async (item: RiskItem) => {
    if (item.type === 'alert') {
      try {
        const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${item.id}/acknowledge`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ acknowledged_by: user?.id || 1 })
        })
        
        if (response.ok) {
          await loadUnifiedRiskItems()
          await loadDashboardStats()
        }
      } catch (err) {
        console.error('Error acknowledging alert:', err)
      }
    }
  }

  const handleResolve = async (item: RiskItem) => {
    if (item.type === 'alert') {
      try {
        const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${item.id}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ resolved_by: user?.id || 1, resolution_notes: 'Resolved from Risk Management dashboard' })
        })
        
        if (response.ok) {
          await loadUnifiedRiskItems()
          await loadDashboardStats()
        }
      } catch (err) {
        console.error('Error resolving alert:', err)
      }
    }
  }

  const filteredItems = useMemo(() => {
    let filtered = [...riskItems]
    
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase()
      filtered = filtered.filter(item => 
        item.property_name?.toLowerCase().includes(query) ||
        item.title?.toLowerCase().includes(query) ||
        item.description?.toLowerCase().includes(query)
      )
    }
    
    if (filters.severity) {
      filtered = filtered.filter(item => item.severity === filters.severity)
    }
    
    if (filters.status) {
      filtered = filtered.filter(item => item.status === filters.status)
    }
    
    return filtered
  }, [riskItems, filters])

  const exportData = async (format: 'excel' | 'csv') => {
    try {
      const params = new URLSearchParams()
      if (filters.propertyId) params.append('property_id', filters.propertyId.toString())
      if (filters.documentType) params.append('document_type', filters.documentType)
      
      const endpoint = format === 'excel' 
        ? `${API_BASE_URL}/anomalies/export/excel`
        : `${API_BASE_URL}/anomalies/export/csv`
      
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        credentials: 'include'
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `risk-management-export.${format === 'excel' ? 'xlsx' : 'csv'}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (err) {
      console.error('Export failed:', err)
      alert('Failed to export data')
    }
  }

  return (
    <div className="risk-management-dashboard" style={{ padding: '2rem', maxWidth: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield style={{ color: '#3b82f6' }} size={32} />
              Risk Management
            </h1>
            <p style={{ color: '#6b7280', margin: '0.5rem 0 0 0' }}>
              Comprehensive Risk Monitoring & Workflow Controls
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`btn btn-sm ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
              title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
            >
              {autoRefresh ? <Activity size={16} /> : <EyeOff size={16} />}
            </button>
            <button
              onClick={() => {
                loadDashboardStats()
                loadUnifiedRiskItems()
              }}
              className="btn btn-sm btn-secondary"
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
            <ExportButton onExport={exportData} />
          </div>
        </div>

        {/* KPI Cards */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <KPICard
            title="Critical Alerts"
            value={dashboardStats.total_critical_alerts}
            icon={<AlertTriangle size={24} />}
            color="#dc2626"
            trend={dashboardStats.total_critical_alerts > 0 ? 'up' : 'neutral'}
          />
          <KPICard
            title="Active Alerts"
            value={dashboardStats.total_active_alerts}
            icon={<AlertTriangle size={24} />}
            color="#f59e0b"
          />
          <KPICard
            title="Active Locks"
            value={dashboardStats.total_active_locks}
            icon={<Lock size={24} />}
            color="#8b5cf6"
          />
          <KPICard
            title="Anomalies"
            value={dashboardStats.total_anomalies}
            icon={<BarChart3 size={24} />}
            color="#3b82f6"
          />
          <KPICard
            title="Properties at Risk"
            value={dashboardStats.properties_at_risk}
            icon={<Shield size={24} />}
            color="#ef4444"
            subtitle={`of ${dashboardStats.total_properties} total`}
          />
          <KPICard
            title="SLA Compliance"
            value={`${dashboardStats.sla_compliance_rate.toFixed(1)}%`}
            icon={<CheckCircle size={24} />}
            color={dashboardStats.sla_compliance_rate >= 95 ? '#10b981' : '#f59e0b'}
          />
        </div>
      </div>

      {/* Property Selector */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Select Property
        </label>
        <select
          value={selectedProperty || ''}
          onChange={(e) => {
            const propId = e.target.value ? parseInt(e.target.value) : null
            setSelectedProperty(propId)
            setFilters(prev => ({ ...prev, propertyId: propId }))
          }}
          className="select-input"
          style={{ width: '100%', maxWidth: '400px', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
        >
          <option value="">All Properties</option>
          {properties.map(prop => (
            <option key={prop.id} value={prop.id}>
              {prop.property_name} - {prop.property_code}
            </option>
          ))}
        </select>
      </div>

      {/* View Mode Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '0.5rem', 
        marginBottom: '1.5rem',
        borderBottom: '2px solid #e5e7eb',
        paddingBottom: '0.5rem'
      }}>
        {(['unified', 'anomalies', 'alerts', 'locks', 'analytics'] as ViewMode[]).map(mode => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`btn btn-sm ${viewMode === mode ? 'btn-primary' : 'btn-secondary'}`}
            style={{ textTransform: 'capitalize' }}
          >
            {mode === 'unified' && <Activity size={16} style={{ marginRight: '0.25rem' }} />}
            {mode}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setShowBatchForm(!showBatchForm)}
            className="btn btn-sm btn-primary"
          >
            <Zap size={16} style={{ marginRight: '0.25rem' }} />
            Batch Operations
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ 
        display: 'flex', 
        gap: '1rem', 
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flex: 1, minWidth: '200px' }}>
          <Search size={16} style={{ color: '#6b7280' }} />
          <input
            type="text"
            placeholder="Search risks..."
            value={filters.searchQuery}
            onChange={(e) => setFilters(prev => ({ ...prev, searchQuery: e.target.value }))}
            className="form-input"
            style={{ flex: 1, padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
          />
        </div>
        <select
          value={filters.severity}
          onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
          className="select-input"
          style={{ minWidth: '150px', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
          className="select-input"
          style={{ minWidth: '150px', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="resolved">Resolved</option>
          <option value="acknowledged">Acknowledged</option>
        </select>
        <select
          value={filters.documentType}
          onChange={(e) => setFilters(prev => ({ ...prev, documentType: e.target.value }))}
          className="form-select"
          style={{ minWidth: '180px' }}
        >
          <option value="">All Document Types</option>
          <option value="income_statement">Income Statement</option>
          <option value="balance_sheet">Balance Sheet</option>
          <option value="cash_flow">Cash Flow</option>
          <option value="rent_roll">Rent Roll</option>
          <option value="mortgage_statement">Mortgage Statement</option>
        </select>
      </div>

      {/* Batch Operations Panel */}
      {showBatchForm && (
        <div style={{ marginBottom: '2rem' }}>
          <BatchReprocessingForm />
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ minHeight: '400px' }}>
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {viewMode === 'unified' && (
          <RiskWorkbenchTable
            items={filteredItems}
            loading={loading}
            onItemClick={handleItemClick}
            onAcknowledge={handleAcknowledge}
            onResolve={handleResolve}
          />
        )}

        {viewMode === 'analytics' && (
          <div className="card">
            <h3>Risk Analytics</h3>
            <p style={{ color: '#6b7280' }}>
              Analytics view coming soon. This will include trend analysis, risk scoring, and predictive insights.
            </p>
          </div>
        )}
      </div>

      {/* Detail Modals */}
      {selectedDetail?.type === 'anomaly' && (
        <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto' }}>
            <AnomalyDetail 
              anomalyId={selectedDetail.id} 
              onClose={() => setSelectedDetail(null)}
            />
          </div>
        </div>
      )}

      {selectedDetail?.type === 'alert' && (
        <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto' }}>
            <AlertDetailView 
              alertId={selectedDetail.id}
              onClose={() => setSelectedDetail(null)}
              onAcknowledge={async (id) => {
                await handleAcknowledge({ id } as RiskItem)
                setSelectedDetail(null)
              }}
              onResolve={async (id) => {
                await handleResolve({ id } as RiskItem)
                setSelectedDetail(null)
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// KPI Card Component
interface KPICardProps {
  title: string
  value: number | string
  icon: React.ReactNode
  color: string
  trend?: 'up' | 'down' | 'neutral'
  subtitle?: string
}

function KPICard({ title, value, icon, color, trend, subtitle }: KPICardProps) {
  return (
    <div className="card" style={{ 
      borderLeft: `4px solid ${color}`,
      padding: '1rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ color, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {icon}
          <span style={{ fontSize: '0.875rem', fontWeight: '500', color: '#6b7280' }}>{title}</span>
        </div>
        {trend && trend !== 'neutral' && (
          trend === 'up' ? <TrendingUp size={16} color={color} /> : <TrendingDown size={16} color="#10b981" />
        )}
      </div>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
          {subtitle}
        </div>
      )}
    </div>
  )
}
