/**
 * Financial Data Viewer Page
 * 
 * View extracted financial data with inline quality indicators
 * - Table view with quality badges
 * - Filter by review status and severity
 * - Match info tooltips
 * - Bulk actions
 */

import { useState, useEffect } from 'react'
import { financialDataService } from '../lib/financial_data'
import type { FinancialDataItem, FinancialDataResponse, FinancialDataSummary } from '../lib/financial_data'
import { QualityBadge } from '../components/QualityBadge'
import { MatchInfoTooltip } from '../components/MatchInfoTooltip'
import { ValidationFlagTooltip } from '../components/ValidationFlagTooltip'

interface FinancialDataViewerProps {
  uploadId: number
  onClose?: () => void
}

export default function FinancialDataViewer({ uploadId, onClose }: FinancialDataViewerProps) {
  const [data, setData] = useState<FinancialDataResponse | null>(null)
  const [summary, setSummary] = useState<FinancialDataSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'needs_review' | 'critical'>('all')
  const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set())
  
  useEffect(() => {
    loadData()
  }, [uploadId, filter])
  
  const loadData = async () => {
    try {
      setLoading(true)
      
      // Determine filter params
      const params: any = {}
      if (filter === 'needs_review') {
        params.filter_needs_review = true
      } else if (filter === 'critical') {
        params.filter_critical = true
      }
      
      const [dataResult, summaryResult] = await Promise.all([
        financialDataService.getFinancialData(uploadId, params),
        financialDataService.getSummary(uploadId)
      ])
      
      setData(dataResult)
      setSummary(summaryResult)
    } catch (error) {
      console.error('Failed to load financial data:', error)
      alert('Failed to load financial data')
    } finally {
      setLoading(false)
    }
  }
  
  const getSeverityIcon = (severity: string) => {
    if (severity === 'critical') return '⚠️'
    if (severity === 'warning') return '⚡'
    return '✅'
  }
  
  const isRentRoll = data?.document_type === 'rent_roll'
  
  const toggleSelectItem = (itemId: number) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId)
    } else {
      newSelected.add(itemId)
    }
    setSelectedItems(newSelected)
  }
  
  const toggleSelectAll = () => {
    if (selectedItems.size === data?.items.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(data?.items.map(item => item.id) || []))
    }
  }
  
  const formatAmount = (amounts: FinancialDataItem['amounts']) => {
    // Try to find the primary amount field
    const amount = amounts.amount || amounts.period_amount || amounts.monthly_rent
    if (amount !== undefined && amount !== null) {
      return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    return '-'
  }
  
  const formatAmounts = (amounts: FinancialDataItem['amounts']) => {
    const parts = []
    if (amounts.period_amount !== undefined && amounts.period_amount !== null) {
      parts.push(`Period: $${amounts.period_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
    }
    if (amounts.ytd_amount !== undefined && amounts.ytd_amount !== null) {
      parts.push(`YTD: $${amounts.ytd_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
    }
    if (amounts.amount !== undefined && amounts.amount !== null) {
      parts.push(`$${amounts.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
    }
    if (amounts.monthly_rent !== undefined && amounts.monthly_rent !== null) {
      parts.push(`$${amounts.monthly_rent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
    }
    return parts.join(' | ') || '-'
  }
  
  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading financial data...</div>
      </div>
    )
  }
  
  if (!data || !summary) {
    return (
      <div className="page">
        <div className="empty-state">No data available</div>
      </div>
    )
  }
  
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Financial Data Viewer</h1>
          <p className="page-subtitle">
            {data.property_code} - {data.document_type.replace('_', ' ')} - {data.period_year}/{String(data.period_month).padStart(2, '0')}
          </p>
        </div>
        <div className="header-actions">
          {onClose && (
            <button onClick={onClose} className="btn-secondary">
              Close
            </button>
          )}
        </div>
      </div>
      
      <div className="page-content">
        {/* Summary Cards */}
        <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: '1.5rem' }}>
          <div className="stat-card">
            <div className="stat-content">
              <div className="stat-value">{summary.total_items}</div>
              <div className="stat-label">Total Items</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-content">
              <div className="stat-value">
                {summary.by_severity.critical}
                {summary.by_severity.critical > 0 && (
                  <span style={{ fontSize: '1rem', color: '#dc2626', marginLeft: '0.5rem' }}>⚠️</span>
                )}
              </div>
              <div className="stat-label">Critical Items</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-content">
              <div className="stat-value">{summary.avg_extraction_confidence.toFixed(1)}%</div>
              <div className="stat-label">Avg Extraction</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-content">
              <div className="stat-value">{summary.avg_match_confidence.toFixed(1)}%</div>
              <div className="stat-label">Avg Matching</div>
            </div>
          </div>
        </div>
        
        {/* Filters and Actions */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => setFilter('all')}
                className={filter === 'all' ? 'btn-primary' : 'btn-secondary'}
              >
                All ({summary.total_items})
              </button>
              <button
                onClick={() => setFilter('needs_review')}
                className={filter === 'needs_review' ? 'btn-primary' : 'btn-secondary'}
              >
                Needs Review ({summary.needs_review_count})
              </button>
              <button
                onClick={() => setFilter('critical')}
                className={filter === 'critical' ? 'btn-primary' : 'btn-secondary'}
              >
                Critical Only ({summary.by_severity.critical})
              </button>
            </div>
            
            {selectedItems.size > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  {selectedItems.size} selected
                </span>
                <button className="btn-secondary btn-sm">
                  Approve Selected
                </button>
                <button className="btn-secondary btn-sm">
                  Export Selected
                </button>
              </div>
            )}
          </div>
        </div>
        
        {/* Data Table */}
        <div className="card wide">
          <div className="table-container">
            <table className="data-table financial-data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={selectedItems.size === data.items.length && data.items.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th style={{ width: '50px' }}>Quality</th>
                  {isRentRoll ? (
                    <>
                      <th style={{ width: '100px' }}>Unit</th>
                      <th>Tenant</th>
                      <th style={{ width: '120px', textAlign: 'right' }}>Monthly Rent</th>
                      <th style={{ width: '110px' }}>Lease End</th>
                      <th style={{ width: '80px', textAlign: 'center' }}>Score</th>
                      <th style={{ width: '80px', textAlign: 'center' }}>Flags</th>
                    </>
                  ) : (
                    <>
                      <th style={{ width: '80px' }}>Line</th>
                      <th style={{ width: '120px' }}>Account Code</th>
                      <th>Account Name</th>
                      <th style={{ width: '180px', textAlign: 'right' }}>Amount</th>
                      <th style={{ width: '100px', textAlign: 'center' }}>Confidence</th>
                    </>
                  )}
                  <th style={{ width: '60px', textAlign: 'center' }}>Info</th>
                  <th style={{ width: '100px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map(item => {
                  const rentRollItem = item as any // Cast for rent roll specific fields
                  
                  return (
                    <tr 
                      key={item.id} 
                      className={`severity-${item.severity} ${item.is_total || item.is_subtotal ? 'total-row' : ''}`}
                    >
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedItems.has(item.id)}
                          onChange={() => toggleSelectItem(item.id)}
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span title={item.severity} style={{ fontSize: '1.25rem' }}>
                          {getSeverityIcon(item.severity)}
                        </span>
                      </td>
                      
                      {isRentRoll ? (
                        <>
                          {/* Rent Roll Columns */}
                          <td><strong>{rentRollItem.unit_number}</strong></td>
                          <td>{rentRollItem.tenant_name}</td>
                          <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                            {rentRollItem.amounts?.monthly_rent ? `$${rentRollItem.amounts.monthly_rent.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '-'}
                          </td>
                          <td style={{ fontSize: '0.875rem' }}>
                            {rentRollItem.lease_end_date || '-'}
                          </td>
                          <td style={{ textAlign: 'center', fontSize: '0.875rem', fontWeight: 600 }}>
                            {rentRollItem.validation_score?.toFixed(1) || item.extraction_confidence?.toFixed(1)}%
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(rentRollItem.critical_flag_count > 0 || rentRollItem.warning_flag_count > 0 || rentRollItem.info_flag_count > 0) ? (
                              <span style={{ 
                                fontSize: '0.75rem',
                                padding: '0.125rem 0.375rem',
                                borderRadius: '0.25rem',
                                backgroundColor: rentRollItem.critical_flag_count > 0 ? '#fef2f2' : '#fffbeb',
                                color: rentRollItem.critical_flag_count > 0 ? '#dc2626' : '#f59e0b',
                                fontWeight: 600
                              }}>
                                🚩 {rentRollItem.critical_flag_count + rentRollItem.warning_flag_count + rentRollItem.info_flag_count}
                              </span>
                            ) : (
                              <span style={{ color: '#10b981', fontSize: '0.875rem' }}>✓</span>
                            )}
                          </td>
                        </>
                      ) : (
                        <>
                          {/* Financial Statement Columns */}
                          <td style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                            {item.line_number || '-'}
                          </td>
                          <td>
                            <strong style={{ fontFamily: 'monospace' }}>{item.account_code}</strong>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              {item.account_name}
                              {item.is_total && (
                                <span className="badge" style={{ backgroundColor: '#3b82f6', color: 'white', fontSize: '0.625rem' }}>
                                  TOTAL
                                </span>
                              )}
                              {item.is_subtotal && (
                                <span className="badge" style={{ backgroundColor: '#8b5cf6', color: 'white', fontSize: '0.625rem' }}>
                                  SUBTOTAL
                                </span>
                              )}
                            </div>
                          </td>
                          <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                            {formatAmounts(item.amounts)}
                          </td>
                          <td style={{ textAlign: 'center', fontSize: '0.75rem' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.125rem' }}>
                              <span style={{ fontWeight: 600 }}>
                                E: {item.extraction_confidence.toFixed(0)}%
                              </span>
                              <span style={{ color: '#6b7280' }}>
                                M: {item.match_confidence?.toFixed(0) || 0}%
                              </span>
                            </div>
                          </td>
                        </>
                      )}
                      
                      <td style={{ textAlign: 'center' }}>
                        {isRentRoll ? (
                          <ValidationFlagTooltip
                            validationScore={rentRollItem.validation_score || item.extraction_confidence}
                            flags={rentRollItem.validation_flags || []}
                            criticalCount={rentRollItem.critical_flag_count || 0}
                            warningCount={rentRollItem.warning_flag_count || 0}
                            infoCount={rentRollItem.info_flag_count || 0}
                          />
                        ) : (
                          <MatchInfoTooltip
                            extractionConfidence={item.extraction_confidence}
                            matchConfidence={item.match_confidence || 0}
                            matchStrategy={item.match_strategy || 'unknown'}
                            matchStrategyLabel={item.match_strategy_label || 'Unknown'}
                            matchStrategyDescription={item.match_strategy_description || ''}
                            severity={item.severity}
                          />
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          {item.needs_review && !item.reviewed && (
                            <button className="btn-sm btn-primary" style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                              Review
                            </button>
                          )}
                          {item.reviewed && (
                            <span style={{ fontSize: '0.75rem', color: '#10b981' }}>✓ Reviewed</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          
          {data.items.length === 0 && (
            <div className="empty-state">
              No items match the current filter
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

