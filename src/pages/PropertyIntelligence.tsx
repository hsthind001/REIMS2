import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface PropertyResearch {
  id: number
  property_id: number
  research_type: string
  status: string
  market_data: any
  demographic_data: any
  comparable_properties: any[]
  investment_thesis: string
  key_findings: string[]
  confidence_score: number
  created_at: string
}

export default function PropertyIntelligence() {
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [researchResults, setResearchResults] = useState<PropertyResearch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'market' | 'demographics' | 'comparables' | 'findings'>('market')

  // Fetch properties on mount
  useEffect(() => {
    fetchProperties()
  }, [])

  // Fetch research when property selected
  useEffect(() => {
    if (selectedProperty) {
      fetchPropertyResearch(selectedProperty)
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
      setError('Failed to load properties')
    }
  }

  const fetchPropertyResearch = async (propertyId: number) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/property-research/properties/${propertyId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setResearchResults(data.research || [])
      }
    } catch (err) {
      console.error('Failed to fetch property research:', err)
      setError('Failed to load research data')
    } finally {
      setLoading(false)
    }
  }

  const runNewResearch = async () => {
    if (!selectedProperty) return

    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/property-research/market`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          property_id: selectedProperty,
          research_type: 'comprehensive'
        })
      })

      if (response.ok) {
        const data = await response.json()
        alert('Research completed successfully!')
        fetchPropertyResearch(selectedProperty)
      } else {
        throw new Error('Research failed')
      }
    } catch (err) {
      console.error('Research failed:', err)
      setError('Failed to run research')
    } finally {
      setLoading(false)
    }
  }

  const selectedPropertyData = properties.find(p => p.id === selectedProperty)
  const latestResearch = researchResults.length > 0 ? researchResults[0] : null

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">🔍 Property Intelligence</h1>
          <p className="page-subtitle">AI-Powered Market Research & Competitive Analysis</p>
        </div>
        <button className="btn-primary" onClick={runNewResearch} disabled={loading || !selectedProperty}>
          {loading ? '🔄 Analyzing...' : '🚀 Run New Research'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="grid-layout">
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

          {selectedPropertyData && (
            <div className="property-card" style={{ marginTop: '1rem' }}>
              <h4>{selectedPropertyData.property_name}</h4>
              {selectedPropertyData.address && <p><strong>Address:</strong> {selectedPropertyData.address}</p>}
              <p><strong>Type:</strong> {selectedPropertyData.property_type}</p>
              <p><strong>Square Feet:</strong> {selectedPropertyData.square_feet?.toLocaleString()}</p>
            </div>
          )}
        </div>

        {/* Research Status */}
        <div className="card">
          <h3 className="card-title">Research Overview</h3>
          {latestResearch ? (
            <div>
              <div className="stat-row">
                <span className="stat-label">Confidence Score:</span>
                <span className="stat-value">{latestResearch.confidence_score || 0}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Status:</span>
                <span className={`badge badge-${latestResearch.status === 'completed' ? 'success' : 'warning'}`}>
                  {latestResearch.status}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Research Type:</span>
                <span>{latestResearch.research_type}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Last Updated:</span>
                <span>{new Date(latestResearch.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-muted">No research data available. Run new research to get started.</p>
          )}
        </div>
      </div>

      {/* Research Results */}
      {latestResearch && (
        <>
          {/* Tabs */}
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'market' ? 'active' : ''}`}
              onClick={() => setActiveTab('market')}
            >
              📊 Market Data
            </button>
            <button
              className={`tab ${activeTab === 'demographics' ? 'active' : ''}`}
              onClick={() => setActiveTab('demographics')}
            >
              👥 Demographics
            </button>
            <button
              className={`tab ${activeTab === 'comparables' ? 'active' : ''}`}
              onClick={() => setActiveTab('comparables')}
            >
              🏢 Comparables
            </button>
            <button
              className={`tab ${activeTab === 'findings' ? 'active' : ''}`}
              onClick={() => setActiveTab('findings')}
            >
              💡 Key Findings
            </button>
          </div>

          {/* Tab Content */}
          <div className="card">
            {activeTab === 'market' && (
              <div>
                <h3 className="card-title">Market Analysis</h3>
                {latestResearch.market_data ? (
                  <div className="data-grid">
                    {Object.entries(latestResearch.market_data).map(([key, value]) => (
                      <div key={key} className="data-item">
                        <span className="data-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="data-value">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted">No market data available</p>
                )}
              </div>
            )}

            {activeTab === 'demographics' && (
              <div>
                <h3 className="card-title">Demographic Analysis</h3>
                {latestResearch.demographic_data ? (
                  <div className="data-grid">
                    {Object.entries(latestResearch.demographic_data).map(([key, value]) => (
                      <div key={key} className="data-item">
                        <span className="data-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="data-value">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted">No demographic data available</p>
                )}
              </div>
            )}

            {activeTab === 'comparables' && (
              <div>
                <h3 className="card-title">Comparable Properties</h3>
                {latestResearch.comparable_properties && latestResearch.comparable_properties.length > 0 ? (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Property Name</th>
                          <th>Address</th>
                          <th>Type</th>
                          <th>Square Feet</th>
                          <th>Cap Rate</th>
                          <th>Similarity Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {latestResearch.comparable_properties.map((comp, idx) => (
                          <tr key={idx}>
                            <td>{comp.name || 'N/A'}</td>
                            <td>{comp.address || 'N/A'}</td>
                            <td>{comp.type || 'N/A'}</td>
                            <td>{comp.square_feet?.toLocaleString() || 'N/A'}</td>
                            <td>{comp.cap_rate || 'N/A'}</td>
                            <td>
                              <span className="badge badge-info">{comp.similarity_score || 0}%</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-muted">No comparable properties found</p>
                )}
              </div>
            )}

            {activeTab === 'findings' && (
              <div>
                <h3 className="card-title">Investment Thesis</h3>
                {latestResearch.investment_thesis && (
                  <div className="thesis-card">
                    <p>{latestResearch.investment_thesis}</p>
                  </div>
                )}

                <h3 className="card-title" style={{ marginTop: '2rem' }}>Key Findings</h3>
                {latestResearch.key_findings && latestResearch.key_findings.length > 0 ? (
                  <ul className="findings-list">
                    {latestResearch.key_findings.map((finding, idx) => (
                      <li key={idx} className="finding-item">
                        <span className="finding-icon">✓</span>
                        <span>{finding}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted">No key findings available</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
