import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface DocumentSummary {
  id: number
  property_id: number
  document_type: string
  document_name: string
  status: string
  executive_summary: string
  detailed_summary: string
  key_points: string[]
  lease_data: any
  om_data: any
  confidence_score: number
  has_hallucination_flag: boolean
  processing_time_seconds: number
  created_at: string
}

export default function DocumentSummarization() {
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [summaries, setSummaries] = useState<DocumentSummary[]>([])
  const [selectedSummary, setSelectedSummary] = useState<DocumentSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [documentType, setDocumentType] = useState<'lease' | 'om'>('lease')
  const [documentText, setDocumentText] = useState('')

  useEffect(() => {
    fetchProperties()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchSummaries(selectedProperty)
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

  const fetchSummaries = async (propertyId: number) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/document-summary/properties/${propertyId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setSummaries(data.summaries || [])
      }
    } catch (err) {
      console.error('Failed to fetch summaries:', err)
    } finally {
      setLoading(false)
    }
  }

  const generateSummary = async () => {
    if (!selectedProperty || !documentText.trim()) {
      setError('Please select a property and enter document text')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const endpoint = documentType === 'lease'
        ? `${API_BASE_URL}/document-summary/lease`
        : `${API_BASE_URL}/document-summary/om`

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          property_id: selectedProperty,
          document_name: `${documentType.toUpperCase()} - ${Date.now()}`,
          document_path: `/uploads/${documentType}s/`,
          document_text: documentText,
          created_by: 1
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          alert('Document summarized successfully!')
          setShowUpload(false)
          setDocumentText('')
          fetchSummaries(selectedProperty)
        } else {
          setError(data.error || 'Summarization failed')
        }
      } else {
        throw new Error('Summarization failed')
      }
    } catch (err) {
      console.error('Summarization failed:', err)
      setError('Failed to generate summary')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">📄 Document Summarization</h1>
          <p className="page-subtitle">AI-Powered Lease & OM Analysis</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => setShowUpload(!showUpload)}
        >
          {showUpload ? '❌ Cancel' : '➕ New Summary'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
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
              {p.property_name}{p.address ? ` - ${p.address}` : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Upload Form */}
      {showUpload && (
        <div className="card">
          <h3 className="card-title">Generate New Summary</h3>
          <div className="form-group">
            <label>Document Type</label>
            <select
              className="form-input"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value as 'lease' | 'om')}
            >
              <option value="lease">Lease Agreement</option>
              <option value="om">Offering Memorandum (OM)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Document Text</label>
            <textarea
              className="form-input"
              rows={10}
              placeholder="Paste document text here..."
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
            />
          </div>
          <button
            className="btn-primary"
            onClick={generateSummary}
            disabled={loading}
          >
            {loading ? '🔄 Analyzing...' : '🚀 Generate Summary'}
          </button>
        </div>
      )}

      {/* Summaries List */}
      <div className="grid-layout-2">
        {/* List */}
        <div className="card">
          <h3 className="card-title">Document Summaries ({summaries.length})</h3>
          {summaries.length > 0 ? (
            <div className="summaries-list">
              {summaries.map((summary) => (
                <div
                  key={summary.id}
                  className={`summary-item ${selectedSummary?.id === summary.id ? 'active' : ''}`}
                  onClick={() => setSelectedSummary(summary)}
                >
                  <div className="summary-header">
                    <strong>{summary.document_name}</strong>
                    <span className={`badge badge-${summary.status === 'completed' ? 'success' : 'warning'}`}>
                      {summary.status}
                    </span>
                  </div>
                  <div className="summary-meta">
                    <span>{summary.document_type}</span>
                    <span>•</span>
                    <span>{summary.confidence_score}% confidence</span>
                    <span>•</span>
                    <span>{new Date(summary.created_at).toLocaleDateString()}</span>
                  </div>
                  {summary.has_hallucination_flag && (
                    <div className="warning-badge">⚠️ Quality Issues Detected</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No summaries yet. Generate your first summary!</p>
            </div>
          )}
        </div>

        {/* Detail */}
        <div className="card">
          <h3 className="card-title">Summary Details</h3>
          {selectedSummary ? (
            <div className="summary-detail">
              {/* Executive Summary */}
              <div className="detail-section">
                <h4>Executive Summary</h4>
                <p>{selectedSummary.executive_summary || 'N/A'}</p>
              </div>

              {/* Confidence Score */}
              <div className="detail-section">
                <h4>Quality Metrics</h4>
                <div className="confidence-bar">
                  <div className="confidence-label">
                    Confidence: {selectedSummary.confidence_score || 0}%
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${selectedSummary.confidence_score || 0}%` }}
                    />
                  </div>
                </div>
                <p>Processing Time: {selectedSummary.processing_time_seconds}s</p>
              </div>

              {/* Key Points */}
              {selectedSummary.key_points && selectedSummary.key_points.length > 0 && (
                <div className="detail-section">
                  <h4>Key Points</h4>
                  <ul className="findings-list">
                    {selectedSummary.key_points.map((point, idx) => (
                      <li key={idx} className="finding-item">
                        <span className="finding-icon">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Lease Data */}
              {selectedSummary.lease_data && (
                <div className="detail-section">
                  <h4>Lease Details</h4>
                  <div className="data-grid">
                    {Object.entries(selectedSummary.lease_data).map(([key, value]) => (
                      <div key={key} className="data-item">
                        <span className="data-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="data-value">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* OM Data */}
              {selectedSummary.om_data && (
                <div className="detail-section">
                  <h4>OM Details</h4>
                  <div className="data-grid">
                    {Object.entries(selectedSummary.om_data).map(([key, value]) => (
                      <div key={key} className="data-item">
                        <span className="data-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="data-value">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed Summary */}
              {selectedSummary.detailed_summary && (
                <div className="detail-section">
                  <h4>Detailed Summary</h4>
                  <p>{selectedSummary.detailed_summary}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <p>Select a summary to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
