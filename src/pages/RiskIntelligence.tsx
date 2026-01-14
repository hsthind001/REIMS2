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
  Shield, AlertTriangle, Lock, TrendingUp, 
  RefreshCw, Filter, Search, Download, Settings, BarChart3,
  CheckCircle, XCircle, Clock, Activity, Zap, Eye, EyeOff, Trash2
} from 'lucide-react'
import { 
  Card, 
  Button, 
  MetricCard, 
  Select, 
  Input, 
  type SelectOption 
} from '../components/ui'
import { propertyService } from '../lib/property'
import { anomaliesService } from '../lib/anomalies'
import { workflowLockService, type WorkflowLock } from '../lib/workflowLocks'
import RiskWorkbenchTable, { type RiskItem } from '../components/risk-workbench/RiskWorkbenchTable'
import { BatchReprocessingForm } from '../components/anomalies/BatchReprocessingForm'
import { ExportButton } from '../components/ExportButton'
import { useAuth } from '../components/AuthContext'
import AlertDetailView from '../components/alerts/AlertDetailView'
import ValueSetupPanel from '../components/risk/ValueSetupPanel'

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

type ViewMode = 'unified' | 'anomalies' | 'alerts' | 'locks' | 'analytics' | 'value_setup'
type DetailView = 'alert' | null

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
    searchQuery: '',
    period: ''
  })
  const [periodOptions, setPeriodOptions] = useState<{ value: string; label: string }[]>([])
  
  // Detail views
  const [selectedDetail, setSelectedDetail] = useState<{ type: DetailView; id: number } | null>(null)
  const [showBatchForm, setShowBatchForm] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(30000) // 30 seconds

  // Load properties on mount
  useEffect(() => {
    fetchProperties()
    fetchPeriods()
  }, [])

  useEffect(() => {
    fetchPeriods()
  }, [selectedProperty])

  const shouldLoadRiskItems = ['unified', 'anomalies', 'alerts', 'locks'].includes(viewMode)

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return
    
    const interval = setInterval(() => {
      loadDashboardStats()
      if (shouldLoadRiskItems) {
        loadUnifiedRiskItems()
      }
    }, refreshInterval)
    
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, viewMode, filters, shouldLoadRiskItems])

  // Load data when filters or view changes
  useEffect(() => {
    loadDashboardStats()
    if (shouldLoadRiskItems) {
      loadUnifiedRiskItems()
    }
  }, [
    selectedProperty,
    viewMode,
    filters.propertyId,
    filters.period,
    filters.documentType,
    shouldLoadRiskItems
  ])

  const fetchProperties = async () => {
    try {
      const props = await propertyService.getAllProperties()
      if (props && Array.isArray(props)) {
        setProperties(props)
        setDashboardStats(prev => ({ ...prev, total_properties: props.length }))
      } else {
        setProperties([])
        setDashboardStats(prev => ({ ...prev, total_properties: 0 }))
      }
    } catch (err: any) {
      console.error('Failed to fetch properties:', err)
      setProperties([])
      setDashboardStats(prev => ({ ...prev, total_properties: 0 }))
    }
  }

  const fetchPeriods = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedProperty) {
        params.append('property_id', selectedProperty.toString())
      }

      const response = await fetch(
        `${API_BASE_URL}/financial-periods/${params.toString() ? `?${params.toString()}` : ''}`,
        { credentials: 'include' }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      if (!Array.isArray(data)) {
        setPeriodOptions([])
        return
      }

      const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
      ]

      const uniquePeriods = new Map<string, string>()
      data.forEach((period: any) => {
        const year = Number(period.period_year)
        const month = Number(period.period_month)
        if (!Number.isFinite(year) || !Number.isFinite(month)) {
          return
        }
        const value = `${year}-${String(month).padStart(2, '0')}`
        const monthLabel = month >= 1 && month <= 12 ? monthNames[month - 1] : 'Unknown'
        uniquePeriods.set(value, `${value} (${monthLabel})`)
      })

      const sorted = Array.from(uniquePeriods.entries())
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => {
          const [aYear, aMonth] = a.value.split('-').map(Number)
          const [bYear, bMonth] = b.value.split('-').map(Number)
          if (aYear !== bYear) return bYear - aYear
          return bMonth - aMonth
        })

      setPeriodOptions(sorted)

      if (filters.period && !uniquePeriods.has(filters.period)) {
        setFilters(prev => ({ ...prev, period: '' }))
      }
    } catch (err) {
      console.error('Failed to fetch periods:', err)
      setPeriodOptions([])
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
        const criticalAlerts = alertsData.total_critical_alerts
          ?? alertsData.critical_alerts
          ?? alertsData.summary?.critical_alerts
          ?? 0
        const activeAlerts = alertsData.total_active_alerts
          ?? alertsData.active_alerts
          ?? alertsData.summary?.active_alerts
          ?? 0
        const propertiesAtRisk = alertsData.properties_at_risk
          ?? alertsData.summary?.properties_at_risk
          ?? 0
        const slaComplianceRate = alertsData.sla_compliance_rate
          ?? alertsData.summary?.sla_compliance_rate
          ?? 0
        setDashboardStats(prev => ({
          ...prev,
          total_critical_alerts: criticalAlerts,
          total_active_alerts: activeAlerts,
          properties_at_risk: propertiesAtRisk,
          avg_resolution_time_hours: alertsData.avg_resolution_time_hours || 0,
          sla_compliance_rate: slaComplianceRate
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
        `${API_BASE_URL}/risk-workbench/unified?item_type=anomaly&page=1&page_size=1${selectedProperty ? `&property_id=${selectedProperty}` : ''}`,
        { credentials: 'include' }
      )
      
      if (anomaliesResponse.ok) {
        const anomaliesData = await anomaliesResponse.json()
        setDashboardStats(prev => ({
          ...prev,
          total_anomalies: anomaliesData.total || 0
        }))
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
      if (viewMode === 'anomalies') params.append('item_type', 'anomaly')
      if (viewMode === 'alerts') params.append('item_type', 'alert')
      if (filters.propertyId) params.append('property_id', filters.propertyId.toString())
      if (filters.documentType) params.append('document_type', filters.documentType)
      if (filters.severity) params.append('severity', filters.severity)
      if (filters.period) params.append('period', filters.period)
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
      
      // Ensure data.items exists and is an array
      if (!data || !Array.isArray(data.items)) {
        console.warn('Invalid response format:', data)
        setRiskItems([])
        return
      }
      
      // Get property names map for better display
      const propertyMap = new Map((properties || []).map(p => [p.property_code, p.property_name]))
      
      // Transform to RiskItem format
      const transformedItems: RiskItem[] = data.items.map((item: any) => {
        const propertyCode = item.property || item.property_code
        const propertyName = propertyMap.get(propertyCode) || propertyCode || 'Unknown Property'
        const accountCode = item.account_code || item.field_name || item.metadata?.account_code
        const accountName = item.account_name || item.metadata?.account_name || item.metadata?.account_description
        
        return {
          id: item.id,
          type: item.type,
          severity: item.severity?.toLowerCase() || 'medium',
          property_id: filters.propertyId || 0,
          property_name: propertyName,
          account_code: accountCode,
          account_name: accountName,
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
      
    } catch (err: any) {
      setError(err.message || 'Failed to load risk items')
      console.error('Error loading risk items:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = useCallback((item: RiskItem) => {
    if (item.type === 'anomaly') {
      window.location.hash = `anomaly-details?anomaly_id=${item.id}`
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

  const handleDelete = async (item: RiskItem) => {
    if (item.type !== 'alert') {
      alert('Only alerts can be deleted from this view')
      return
    }

    if (!confirm(`Are you sure you want to delete this alert and all related anomalies/warnings/alerts for this property? This action cannot be undone.`)) {
      return
    }

    try {
      // Get property ID from the item - try multiple sources
      let propertyId: number | null = null
      
      if (item.property_id && item.property_id > 0) {
        propertyId = item.property_id
      } else if (item.metadata?.property_id) {
        propertyId = parseInt(item.metadata.property_id)
      } else if (filters.propertyId) {
        propertyId = filters.propertyId
      } else if (selectedProperty) {
        propertyId = selectedProperty
      } else {
        // Try to find property by code from metadata
        const propertyCode = item.metadata?.property_code || item.property_name
        if (propertyCode) {
          const property = properties.find(p => 
            p.property_code === propertyCode || 
            p.property_name === propertyCode
          )
          if (property) {
            propertyId = property.id
          }
        }
      }
      
      if (!propertyId || propertyId <= 0) {
        alert('Could not determine property for this alert. Please select a property filter or use bulk delete.')
        return
      }

      await deleteAlertsForProperty(propertyId)
    } catch (err: any) {
      console.error('Error deleting alert:', err)
      alert(`Failed to delete alert: ${err.message || 'Unknown error'}`)
    }
  }

  const deleteAlertsForProperty = async (propertyId: number) => {
    try {
      const params = new URLSearchParams()
      params.append('property_ids', propertyId.toString())
      
      // Apply current filters
      if (filters.documentType) {
        params.append('document_type', filters.documentType)
      }

      const response = await fetch(`${API_BASE_URL}/documents/anomalies-warnings-alerts/delete-filtered?${params}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        alert(`Successfully deleted ${data.total_deleted} records (alerts, anomalies, etc.)`)
        await loadUnifiedRiskItems()
        await loadDashboardStats()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (err: any) {
      throw new Error(err.message || 'Failed to delete alerts')
    }
  }

  const handleBulkDeleteAlerts = async () => {
    const alertItems = filteredItems.filter(item => item.type === 'alert')
    
    if (alertItems.length === 0) {
      alert('No alerts to delete')
      return
    }

    // Get unique property IDs from alerts
    const propertyIds = Array.from(new Set(
      alertItems
        .map(item => {
          if (item.property_id) return item.property_id
          const property = properties.find(p => p.property_code === item.metadata?.property_code)
          return property?.id
        })
        .filter((id): id is number => id !== undefined && id !== null)
    ))

    if (propertyIds.length === 0) {
      alert('Could not determine properties for alerts. Please use the Data Control Center to delete.')
      return
    }

    const confirmMessage = `Are you sure you want to delete all alerts for ${propertyIds.length} property(ies)?\n\n` +
      `This will delete:\n` +
      `- ${alertItems.length} alert(s) currently visible\n` +
      `- All related anomalies, warnings, and alerts for the selected properties\n\n` +
      `This action cannot be undone.`

    if (!confirm(confirmMessage)) {
      return
    }

    try {
      const params = new URLSearchParams()
      propertyIds.forEach(id => params.append('property_ids', id.toString()))
      
      // Apply current filters
      if (filters.documentType) {
        params.append('document_type', filters.documentType)
      }

      const response = await fetch(`${API_BASE_URL}/documents/anomalies-warnings-alerts/delete-filtered?${params}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        alert(`Successfully deleted ${data.total_deleted} records!\n\n` +
          `- Anomalies: ${data.deletion_counts.anomaly_detections}\n` +
          `- Alerts: ${data.deletion_counts.alerts}\n` +
          `- Committee Alerts: ${data.deletion_counts.committee_alerts}`)
        await loadUnifiedRiskItems()
        await loadDashboardStats()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (err: any) {
      console.error('Error bulk deleting alerts:', err)
      alert(`Failed to delete alerts: ${err.message || 'Unknown error'}`)
    }
  }

  const filteredItems = useMemo(() => {
    if (!riskItems || !Array.isArray(riskItems)) {
      return []
    }
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

  const visibleItems = useMemo(() => {
    if (viewMode === 'anomalies') {
      return filteredItems.filter(item => item.type === 'anomaly')
    }
    if (viewMode === 'alerts') {
      return filteredItems.filter(item => item.type === 'alert')
    }
    if (viewMode === 'locks') {
      return []
    }
    return filteredItems
  }, [filteredItems, viewMode])

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
    <div className="p-8 w-full max-w-full space-y-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Shield className="text-blue-500" size={32} />
              Risk Management
            </h1>
            <p className="text-gray-600 mt-2">
              Comprehensive Risk Monitoring & Workflow Controls
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              onClick={() => setAutoRefresh(!autoRefresh)}
              variant={autoRefresh ? 'primary' : 'secondary'}
              size="sm"
              title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
              icon={autoRefresh ? <Activity size={16} /> : <EyeOff size={16} />}
            >
              {autoRefresh ? 'Auto' : 'Manual'}
            </Button>
            <Button
              onClick={() => {
                loadDashboardStats()
                loadUnifiedRiskItems()
              }}
              variant="secondary"
              size="sm"
              loading={loading}
              icon={<RefreshCw size={16} />}
            >
              Refresh
            </Button>
            <ExportButton onExport={exportData} />
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <MetricCard
            title="Critical Alerts"
            value={dashboardStats.total_critical_alerts.toLocaleString()}
            status="danger"
            trend={dashboardStats.total_critical_alerts > 0 ? 'up' : 'neutral'}
            comparison="Active critical issues"
            loading={loading}
          />
          <MetricCard
            title="Active Alerts"
            value={dashboardStats.total_active_alerts.toLocaleString()}
            status="warning"
            comparison="All severities"
            loading={loading}
          />
          <MetricCard
            title="Active Locks"
            value={dashboardStats.total_active_locks.toLocaleString()}
            status="info"
            comparison="Current period locks"
            loading={loading}
          />
          <MetricCard
            title="Anomalies"
            value={dashboardStats.total_anomalies.toLocaleString()}
            status="warning"
            comparison="Open anomalies"
            loading={loading}
          />
          <MetricCard
            title="Properties at Risk"
            value={dashboardStats.properties_at_risk.toLocaleString()}
            status="danger"
            comparison={`of ${dashboardStats.total_properties} total`}
            loading={loading}
          />
          <MetricCard
            title="SLA Compliance"
            value={`${dashboardStats.sla_compliance_rate.toFixed(1)}%`}
            status={dashboardStats.sla_compliance_rate >= 95 ? 'success' : 'warning'}
            comparison="Target ≥95%"
            loading={loading}
          />
        </div>
      </div>

      {/* Property Selector */}
      <div className="mb-6 w-full max-w-sm">
        <Select
          label="Select Property"
          value={selectedProperty ? String(selectedProperty) : ''}
          onChange={(val) => {
            const propId = val ? parseInt(val) : null
            setSelectedProperty(propId)
            setFilters(prev => ({ ...prev, propertyId: propId }))
          }}
          options={[
            { value: '', label: 'All Properties' },
            ...properties.map(prop => ({
              value: String(prop.id),
              label: `${prop.property_name} - ${prop.property_code}`
            }))
          ]}
          searchable
        />
      </div>

      {/* Quick Access Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card 
          interactive 
          onClick={() => window.location.hash = 'anomaly-dashboard'}
          className="p-6 cursor-pointer bg-gradient-to-br from-blue-500 to-indigo-600 text-white border-0"
        >
            <div className="text-3xl mb-2">🔍</div>
            <h3 className="text-lg font-semibold mb-2">All Anomalies</h3>
            <p className="text-blue-100 text-sm">Browse and filter all detected anomalies in grid view</p>
        </Card>

        <Card 
          interactive 
          onClick={() => window.location.hash = 'forensic-audit-dashboard'}
          className="p-6 cursor-pointer bg-gradient-to-br from-purple-400 to-pink-500 text-white border-0"
        >
            <div className="text-3xl mb-2">🔬</div>
            <h3 className="text-lg font-semibold mb-2">Forensic Audit Suite</h3>
            <p className="text-pink-100 text-sm">Access 10 specialized audit dashboards</p>
        </Card>
      </div>

      {/* View Mode Tabs using Buttons */}
      <div className="flex gap-2 mb-6 border-b border-gray-200 pb-2 overflow-x-auto">
        {(['unified', 'anomalies', 'alerts', 'locks', 'analytics', 'value_setup'] as ViewMode[]).map(mode => (
          <Button
            key={mode}
            onClick={() => setViewMode(mode)}
            variant={viewMode === mode ? 'primary' : 'secondary'}
            size="sm"
            className="capitalize whitespace-nowrap"
            icon={
              mode === 'unified' ? <Activity size={16} /> :
              mode === 'value_setup' ? <Settings size={16} /> :
              undefined
            }
          >
            {mode === 'value_setup' ? 'Value Setup' : mode}
          </Button>
        ))}
        <div className="ml-auto flex gap-2">
          <Button
            onClick={() => setShowBatchForm(!showBatchForm)}
            variant="primary"
            size="sm"
            icon={<Zap size={16} />}
          >
            Batch Operations
          </Button>
        </div>
      </div>

      {/* Filters */}
      {viewMode !== 'value_setup' && (
        <div className="flex gap-4 mb-6 flex-wrap items-end">
          <div className="flex-1 min-w-[200px]">
             <Input
                placeholder="Search risks..."
                value={filters.searchQuery}
                onChange={(e) => setFilters(prev => ({ ...prev, searchQuery: e.target.value }))}
                leftIcon={<Search size={16} className="text-gray-400" />}
                fullWidth
             />
          </div>
          <div className="w-40">
             <Select
                placeholder="All Severities"
                value={filters.severity}
                onChange={(val) => setFilters(prev => ({ ...prev, severity: val }))}
                options={[
                   { value: '', label: 'All Severities' },
                   { value: 'critical', label: 'Critical' },
                   { value: 'high', label: 'High' },
                   { value: 'medium', label: 'Medium' },
                   { value: 'low', label: 'Low' },
                ]}
             />
          </div>
          <div className="w-40">
             <Select
                placeholder="All Statuses"
                value={filters.status}
                onChange={(val) => setFilters(prev => ({ ...prev, status: val }))}
                options={[
                   { value: '', label: 'All Statuses' },
                   { value: 'active', label: 'Active' },
                   { value: 'resolved', label: 'Resolved' },
                   { value: 'acknowledged', label: 'Acknowledged' },
                ]}
             />
          </div>
          <div className="w-48">
              <Select
                placeholder="All Document Types"
                value={filters.documentType}
                onChange={(val) => setFilters(prev => ({ ...prev, documentType: val }))}
                options={[
                    { value: '', label: 'All Document Types' },
                    { value: 'income_statement', label: 'Income Statement' },
                    { value: 'balance_sheet', label: 'Balance Sheet' },
                    { value: 'cash_flow', label: 'Cash Flow' },
                    { value: 'rent_roll', label: 'Rent Roll' },
                    { value: 'mortgage_statement', label: 'Mortgage Statement' },
                ]}
              />
          </div>
          <div className="w-56">
               <Select
                placeholder="All Periods"
                value={filters.period}
                onChange={(val) => setFilters(prev => ({ ...prev, period: val }))}
                options={[
                    { value: '', label: 'All Periods' },
                    ...periodOptions
                ]}
              />
          </div>
        </div>
      )}

      {/* Batch Operations Panel */}
      {showBatchForm && (
        <div className="mb-8">
          <BatchReprocessingForm />
        </div>
      )}

      {/* Main Content Area */}
      <div className="min-h-[400px]">
        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        )}

        {['unified', 'anomalies', 'alerts', 'locks'].includes(viewMode) && (
          <>
            {viewMode === 'unified' && filteredItems.some(item => item.type === 'alert') && (
              <div className="mb-4 flex justify-end">
                <Button
                  onClick={handleBulkDeleteAlerts}
                  variant="danger"
                  size="sm"
                  icon={<Trash2 size={16} />}
                >
                  Delete All Visible Alerts
                </Button>
              </div>
            )}
            <RiskWorkbenchTable
              items={visibleItems}
              loading={loading}
              onItemClick={handleItemClick}
              onAcknowledge={handleAcknowledge}
              onResolve={handleResolve}
              onDelete={handleDelete}
            />
          </>
        )}

        {viewMode === 'analytics' && (
          <Card className="p-6 text-center">
            <h3 className="text-xl font-semibold mb-2">Risk Analytics</h3>
            <p className="text-gray-600">
              Analytics view coming soon. This will include trend analysis, risk scoring, and predictive insights.
            </p>
          </Card>
        )}

        {viewMode === 'value_setup' && (
          <ValueSetupPanel />
        )}
      </div>

      {/* Detail Modals */}
      {selectedDetail?.type === 'alert' && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedDetail(null)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
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

// Legacy KPI card replaced by premium MetricCard
