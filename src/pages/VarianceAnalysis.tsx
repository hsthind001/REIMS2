import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1'

interface VarianceItem {
  account_code: string
  account_name: string
  previous_period_amount: number
  current_period_amount: number
  variance_amount: number
  variance_percentage: number
  within_tolerance: boolean
  severity: string
  is_favorable: boolean
}

export default function VarianceAnalysis() {
  const [properties, setProperties] = useState<any[]>([])
  const [periods, setPeriods] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null)
  const [variances, setVariances] = useState<VarianceItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<any>(null)
  const [previousPeriodInfo, setPreviousPeriodInfo] = useState<any>(null)

  useEffect(() => {
    fetchProperties()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchPeriods(selectedProperty)
    }
  }, [selectedProperty])

  useEffect(() => {
    if (selectedProperty && selectedPeriod) {
      fetchVariances()
    }
  }, [selectedProperty, selectedPeriod])

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

  const fetchPeriods = async (propertyId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/financial-periods?property_id=${propertyId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setPeriods(data.periods || [])
        if (data.periods && data.periods.length > 0) {
          setSelectedPeriod(data.periods[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to fetch periods:', err)
    }
  }

  const fetchVariances = async () => {
    if (!selectedProperty || !selectedPeriod) return

    setLoading(true)
    setError(null)

    try {
      const endpoint = `${API_BASE_URL}/variance-analysis/properties/${selectedProperty}/periods/${selectedPeriod}/period-over-period`

      const response = await fetch(endpoint, {
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        setVariances(data.variance_items || [])
        setSummary(data.summary)
        setPreviousPeriodInfo({
          year: data.previous_period_year,
          month: data.previous_period_month
        })
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to load variance data')
      }
    } catch (err) {
      console.error('Failed to fetch variances:', err)
      setError('Failed to load variance data')
    } finally {
      setLoading(false)
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
        return 'success'
    }
  }

  const selectedPeriodData = periods.find(p => p.id === selectedPeriod)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">📊 Variance Analysis</h1>
          <p className="page-subtitle">Period-over-Period Actual Performance Comparison</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Filters */}
      <div className="grid-layout">
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
                {p.property_name}
              </option>
            ))}
          </select>
        </div>

        <div className="card">
          <h3 className="card-title">Select Period</h3>
          <select
            className="select-input"
            value={selectedPeriod || ''}
            onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          >
            <option value="">Choose a period...</option>
            {periods.map(p => (
              <option key={p.id} value={p.id}>
                {p.period_name} ({new Date(p.start_date).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && previousPeriodInfo && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">📅</div>
            <div className="stat-info">
              <div className="stat-value">${summary.total_previous_period?.toLocaleString()}</div>
              <div className="stat-label">Previous Period ({previousPeriodInfo.year}/{previousPeriodInfo.month})</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📈</div>
            <div className="stat-info">
              <div className="stat-value">${summary.total_current_period?.toLocaleString()}</div>
              <div className="stat-label">Current Period ({selectedPeriodData?.period_year}/{selectedPeriodData?.period_month})</div>
            </div>
          </div>
          <div className={`stat-card stat-${summary.total_variance_amount >= 0 ? 'success' : 'error'}`}>
            <div className="stat-icon">{summary.total_variance_amount >= 0 ? '✅' : '⚠️'}</div>
            <div className="stat-info">
              <div className="stat-value">${summary.total_variance_amount?.toLocaleString()}</div>
              <div className="stat-label">Total Variance</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <div className="stat-value">{summary.total_variance_percentage?.toFixed(1)}%</div>
              <div className="stat-label">Variance %</div>
            </div>
          </div>
        </div>
      )}

      {/* Variance Table */}
      <div className="card">
        <h3 className="card-title">
          Period-over-Period Variance Details
          {previousPeriodInfo && selectedPeriodData && (
            <span style={{ fontSize: '0.9rem', fontWeight: 'normal', marginLeft: '10px' }}>
              Comparing {previousPeriodInfo.year}/{previousPeriodInfo.month} vs {selectedPeriodData.period_year}/{selectedPeriodData.period_month}
            </span>
          )}
        </h3>
        {variances.length > 0 ? (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Account Code</th>
                  <th>Account Name</th>
                  <th>Previous Period</th>
                  <th>Current Period</th>
                  <th>Variance $</th>
                  <th>Variance %</th>
                  <th>Status</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {variances.map((variance, idx) => (
                  <tr key={idx} className={variance.within_tolerance ? '' : 'highlight-row'}>
                    <td>{variance.account_code}</td>
                    <td>{variance.account_name}</td>
                    <td>${variance.previous_period_amount?.toLocaleString()}</td>
                    <td>${variance.current_period_amount?.toLocaleString()}</td>
                    <td className={variance.variance_amount >= 0 ? 'positive' : 'negative'}>
                      ${variance.variance_amount?.toLocaleString()}
                    </td>
                    <td className={variance.variance_amount >= 0 ? 'positive' : 'negative'}>
                      {variance.variance_percentage?.toFixed(1)}%
                    </td>
                    <td>
                      <span className={`badge badge-${variance.within_tolerance ? 'success' : 'warning'}`}>
                        {variance.within_tolerance ? 'Within Tolerance' : 'Out of Tolerance'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${getSeverityColor(variance.severity)}`}>
                        {variance.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading variance data...</p>
          </div>
        ) : (
          <div className="empty-state">
            <p>No variance data available for the selected property and period.</p>
          </div>
        )}
      </div>
    </div>
  )
}
