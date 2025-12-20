/**
 * Review Queue Page
 * 
 * Full-featured review interface for items needing manual attention
 */

import { useState, useEffect } from 'react'
import { reviewService } from '../lib/review'
import { propertyService } from '../lib/property'
import { QualityBadge } from '../components/QualityBadge'
import { EditRecordModal } from '../components/EditRecordModal'
import type { Property } from '../types/api'

interface ReviewQueueItem {
  record_id: number
  table_name: string
  property_code: string
  property_name: string
  period_year: number
  period_month: number
  account_code?: string
  account_name?: string
  amount?: number
  period_amount?: number
  monthly_rent?: number
  extraction_confidence?: number
  match_confidence?: number
  match_strategy?: string
  needs_review: boolean
  reviewed: boolean
}

export default function ReviewQueue() {
  // Parse severity from URL hash (e.g., review-queue?severity=warning)
  const getSeverityFromHash = (): string => {
    const hash = window.location.hash
    const match = hash.match(/severity=(\w+)/)
    return match ? match[1] : 'all'
  }

  const [reviewItems, setReviewItems] = useState<ReviewQueueItem[]>([])
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    property_code: '',
    document_type: '',
    severity: getSeverityFromHash()
  })
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  
  useEffect(() => {
    loadProperties()
    loadReviewQueue()
  }, [])
  
  useEffect(() => {
    loadReviewQueue()
  }, [filters])
  
  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties()
      setProperties(data)
    } catch (error) {
      console.error('Failed to load properties:', error)
    }
  }
  
  const loadReviewQueue = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (filters.property_code) params.property_code = filters.property_code
      if (filters.document_type) params.document_type = filters.document_type
      
      const data = await reviewService.getReviewQueue(params)
      
      // Filter by severity on frontend (backend returns all)
      let filteredItems = data.items || []
      if (filters.severity !== 'all') {
        filteredItems = filteredItems.filter((item: ReviewQueueItem) => {
          const conf = item.extraction_confidence || 0
          const matchConf = item.match_confidence || 0
          const isMatched = item.account_code && item.account_code !== 'UNMATCHED'
          
          if (filters.severity === 'critical') {
            // Critical: extraction < 85% OR match < 95% OR unmatched
            return conf < 85 || matchConf < 95 || !isMatched
          } else if (filters.severity === 'warning') {
            // Warning: extraction 85-95% AND match >= 95% AND matched
            return conf >= 85 && conf < 95 && matchConf >= 95 && isMatched
          }
          return true
        })
      }
      
      setReviewItems(filteredItems)
    } catch (error) {
      console.error('Failed to load review queue:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleExport = async () => {
    try {
      setExporting(true)
      const blob = await reviewService.exportReviewItems({
        property_code: filters.property_code || undefined,
        document_type: filters.document_type || undefined,
        severity: filters.severity === 'all' ? undefined : filters.severity
      })
      
      // Download file
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `review-items-${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      alert('✅ Excel file downloaded successfully!')
    } catch (error: any) {
      alert(`❌ Export failed: ${error.message || 'Unknown error'}`)
    } finally {
      setExporting(false)
    }
  }
  
  const openEditModal = (item: ReviewQueueItem) => {
    setSelectedItem(item)
    setShowEditModal(true)
  }
  
  const handleSaveEdit = async (updates: any) => {
    if (!selectedItem) return
    
    try {
      await reviewService.correctRecord(
        selectedItem.record_id,
        selectedItem.table_name,
        'account_code',  // Field name
        updates.account_code,
        updates.notes
      )
      
      alert('✅ Record updated successfully!')
      loadReviewQueue()  // Reload
    } catch (error: any) {
      throw new Error(error.message || 'Failed to save changes')
    }
  }
  
  const approveItem = async (item: ReviewQueueItem) => {
    const confirmed = window.confirm(
      `Approve this item?\n\n` +
      `Property: ${item.property_code}\n` +
      `Account: ${item.account_code || 'UNMATCHED'}\n` +
      `Amount: $${(item.amount || item.period_amount || item.monthly_rent || 0).toLocaleString()}`
    )
    
    if (!confirmed) return
    
    try {
      await reviewService.approveRecord(item.record_id, item.table_name, 'Approved from review queue')
      alert('✅ Item approved successfully!')
      loadReviewQueue()
    } catch (error: any) {
      alert(`❌ Approval failed: ${error.message || 'Unknown error'}`)
    }
  }
  
  const getSeverity = (item: ReviewQueueItem): 'critical' | 'warning' | 'info' | 'excellent' => {
    const extractionConf = item.extraction_confidence || 0
    const matchConf = item.match_confidence || 0
    const isMatched = item.account_code && item.account_code !== 'UNMATCHED'
    
    // Critical: extraction < 85% OR match < 95% OR unmatched
    if (extractionConf < 85 || matchConf < 95 || !isMatched) {
      return 'critical'
    } 
    // Warning: extraction 85-95% AND match >= 95% AND matched
    else if (extractionConf >= 85 && extractionConf < 95 && matchConf >= 95 && isMatched) {
      return 'warning'
    }
    // Excellent: extraction >= 95% AND match >= 95%
    return 'excellent'
  }
  
  const getReason = (item: ReviewQueueItem): string => {
    const extractionConf = item.extraction_confidence || 0
    const matchConf = item.match_confidence || 0
    const isMatched = item.account_code && item.account_code !== 'UNMATCHED'
    const reasons = []
    
    if (!isMatched) reasons.push('Unmatched account')
    if (extractionConf < 85) reasons.push(`Low extraction (${extractionConf.toFixed(1)}%)`)
    else if (extractionConf < 95) reasons.push(`Medium extraction (${extractionConf.toFixed(1)}%)`)
    if (matchConf < 95 && matchConf > 0) reasons.push(`Match quality (${matchConf.toFixed(1)}%)`)
    
    return reasons.join('; ') || 'Flagged for review'
  }
  
  const handleBack = () => {
    // Clear hash to go back to Data Control Center
    window.location.hash = ''
  }

  return (
    <div className="page">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            onClick={handleBack}
            className="btn-secondary"
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              padding: '0.5rem 1rem'
            }}
            title="Go back to Data Control Center"
          >
            ← Back
          </button>
          <div>
            <h1>Review Queue</h1>
            <p className="page-subtitle">Items needing manual review or correction</p>
          </div>
        </div>
        <div className="header-actions" style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={handleExport} 
            className="btn-secondary"
            disabled={exporting || reviewItems.length === 0}
          >
            {exporting ? '⏳ Exporting...' : '📥 Export to Excel'}
          </button>
          <button onClick={loadReviewQueue} className="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>
      
      <div className="page-content">
        {/* Filters */}
        <div className="card">
          <h3>Filters</h3>
          <div className="filters-section" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label>Property</label>
              <select 
                value={filters.property_code} 
                onChange={(e) => setFilters({...filters, property_code: e.target.value})}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="">All Properties</option>
                {properties.map(p => (
                  <option key={p.id} value={p.property_code}>{p.property_code} - {p.property_name}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label>Document Type</label>
              <select 
                value={filters.document_type} 
                onChange={(e) => setFilters({...filters, document_type: e.target.value})}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="">All Types</option>
                <option value="balance_sheet">Balance Sheet</option>
                <option value="income_statement">Income Statement</option>
                <option value="cash_flow">Cash Flow</option>
                <option value="rent_roll">Rent Roll</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Severity</label>
              <select 
                value={filters.severity} 
                onChange={(e) => setFilters({...filters, severity: e.target.value})}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="all">All Items</option>
                <option value="critical">Critical Only</option>
                <option value="warning">Warnings Only</option>
              </select>
            </div>
          </div>
        </div>
        
        {/* Review Table */}
        <div className="card wide">
          <h3>Review Items ({reviewItems.length})</h3>
          
          {loading ? (
            <div className="empty-state">Loading review items...</div>
          ) : reviewItems.length === 0 ? (
            <div className="empty-state">
              ✅ No items needing review!
              {(filters.property_code || filters.document_type || filters.severity !== 'all') && (
                <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
                  Try adjusting filters to see more items
                </p>
              )}
            </div>
          ) : (
            <div className="table-container">
              <table className="review-table data-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Property</th>
                    <th>Period</th>
                    <th>Account</th>
                    <th>Amount</th>
                    <th>Confidence</th>
                    <th>Issue</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewItems.map(item => {
                    const severity = getSeverity(item)
                    const reason = getReason(item)
                    const amount = item.amount || item.period_amount || item.monthly_rent || 0
                    
                    return (
                      <tr key={`${item.table_name}-${item.record_id}`} className={`severity-${severity}`}>
                        <td>
                          <QualityBadge 
                            severity={severity} 
                            showIcon={true}
                            detailed={item.match_confidence !== undefined && item.match_confidence !== null}
                            extractionConfidence={item.extraction_confidence}
                            matchConfidence={item.match_confidence}
                          />
                        </td>
                        <td>
                          <strong>{item.property_code}</strong>
                          <br />
                          <small style={{ color: '#6b7280' }}>{item.property_name}</small>
                        </td>
                        <td>{item.period_year}/{item.period_month.toString().padStart(2, '0')}</td>
                        <td>
                          <strong>{item.account_code || 'UNMATCHED'}</strong>
                          <br />
                          <small style={{ color: '#6b7280' }}>{item.account_name || 'No name'}</small>
                        </td>
                        <td style={{ textAlign: 'right' }}>${amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                        <td style={{ textAlign: 'center' }}>
                          {item.extraction_confidence !== undefined && item.extraction_confidence !== null ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.125rem', fontSize: '0.75rem' }}>
                              <span style={{ fontWeight: 600 }}>E: {item.extraction_confidence.toFixed(1)}%</span>
                              {item.match_confidence !== undefined && item.match_confidence !== null && (
                                <span style={{ color: '#6b7280' }}>M: {item.match_confidence.toFixed(1)}%</span>
                              )}
                            </div>
                          ) : (
                            'N/A'
                          )}
                        </td>
                        <td><small>{reason}</small></td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <button 
                              onClick={() => openEditModal(item)}
                              className="btn-sm btn-primary"
                              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            >
                              Edit
                            </button>
                            <button 
                              onClick={() => approveItem(item)}
                              className="btn-sm btn-secondary"
                              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            >
                              Approve
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      
      {/* Edit Modal */}
      {showEditModal && selectedItem && (
        <EditRecordModal
          item={selectedItem}
          onSave={handleSaveEdit}
          onClose={() => {
            setShowEditModal(false)
            setSelectedItem(null)
          }}
        />
      )}
    </div>
  )
}

