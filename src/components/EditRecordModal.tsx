/**
 * Edit Record Modal Component
 * 
 * In-app editing interface for correcting extracted financial data
 */

import { useState, useEffect } from 'react'
import { reviewService } from '../lib/review'

interface ReviewQueueItem {
  record_id: number
  table_name: string
  property_code: string
  account_code?: string
  account_name?: string
  amount?: number
  period_amount?: number
  monthly_rent?: number
  extraction_confidence?: number
}

interface EditRecordModalProps {
  item: ReviewQueueItem
  onSave: (updates: any) => Promise<void>
  onClose: () => void
}

export function EditRecordModal({ item, onSave, onClose }: EditRecordModalProps) {
  const [formData, setFormData] = useState({
    account_code: item.account_code || '',
    account_name: item.account_name || '',
    amount: item.amount || item.period_amount || item.monthly_rent || 0,
    notes: ''
  })
  
  const [saving, setSaving] = useState(false)
  const [accountSuggestions, setAccountSuggestions] = useState<any[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  
  // Fetch account suggestions when user types
  const handleAccountSearch = async (query: string) => {
    if (query.length < 2) {
      setAccountSuggestions([])
      setShowSuggestions(false)
      return
    }
    
    try {
      // Call chart of accounts search endpoint
      const response = await fetch(`/api/v1/chart-of-accounts/search?query=${encodeURIComponent(query)}`)
      if (response.ok) {
        const accounts = await response.json()
        setAccountSuggestions(accounts.slice(0, 10))  // Limit to top 10
        setShowSuggestions(true)
      }
    } catch (error) {
      console.error('Failed to fetch account suggestions:', error)
    }
  }
  
  const selectAccount = (account: any) => {
    setFormData({
      ...formData,
      account_code: account.account_code,
      account_name: account.account_name
    })
    setShowSuggestions(false)
    setAccountSuggestions([])
  }
  
  const handleSave = async () => {
    if (!formData.account_code || !formData.account_name) {
      alert('Please provide both account code and account name')
      return
    }
    
    setSaving(true)
    try {
      await onSave(formData)
      onClose()
    } catch (error: any) {
      alert(`Failed to save: ${error.message || 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Financial Record</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        
        <div className="modal-body">
          <div className="info-section">
            <p><strong>Property:</strong> {item.property_code}</p>
            <p><strong>Original Confidence:</strong> {item.extraction_confidence?.toFixed(1)}%</p>
          </div>
          
          <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #e5e7eb' }} />
          
          <div className="form-group" style={{ position: 'relative' }}>
            <label>Account Code *</label>
            <input 
              type="text"
              value={formData.account_code}
              onChange={(e) => {
                setFormData({...formData, account_code: e.target.value})
                handleAccountSearch(e.target.value)
              }}
              placeholder="e.g., 1010-0000"
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '0.375rem',
                border: '1px solid #d1d5db'
              }}
            />
            
            {showSuggestions && accountSuggestions.length > 0 && (
              <div className="suggestions-dropdown">
                {accountSuggestions.map((acc) => (
                  <div 
                    key={acc.id} 
                    onClick={() => selectAccount(acc)}
                    style={{
                      padding: '0.5rem 1rem',
                      cursor: 'pointer',
                      borderBottom: '1px solid #f3f4f6'
                    }}
                  >
                    <strong>{acc.account_code}</strong> - {acc.account_name}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="form-group">
            <label>Account Name *</label>
            <input 
              type="text"
              value={formData.account_name}
              onChange={(e) => setFormData({...formData, account_name: e.target.value})}
              placeholder="e.g., Cash - Operating Account"
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '0.375rem',
                border: '1px solid #d1d5db'
              }}
            />
          </div>
          
          <div className="form-group">
            <label>Amount *</label>
            <input 
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({...formData, amount: parseFloat(e.target.value) || 0})}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '0.375rem',
                border: '1px solid #d1d5db'
              }}
            />
          </div>
          
          <div className="form-group">
            <label>Correction Notes</label>
            <textarea 
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              placeholder="Describe the correction made..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.5rem',
                borderRadius: '0.375rem',
                border: '1px solid #d1d5db',
                resize: 'vertical'
              }}
            />
          </div>
        </div>
        
        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>
            Cancel
          </button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

