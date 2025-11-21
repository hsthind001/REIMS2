import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface TenantRecommendation {
  id: number
  property_id: number
  recommendation_type: string
  status: string
  recommended_tenants: any[]
  match_criteria: any
  tenant_profile: any
  space_requirements: any
  confidence_score: number
  created_at: string
}

export default function TenantOptimizer() {
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [recommendations, setRecommendations] = useState<TenantRecommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showNewForm, setShowNewForm] = useState(false)
  const [formData, setFormData] = useState({
    space_size: '',
    industry: '',
    min_credit_score: 700,
    lease_term_months: 36
  })

  useEffect(() => {
    fetchProperties()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchRecommendations(selectedProperty)
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

  const fetchRecommendations = async (propertyId: number) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/tenant-recommendations/properties/${propertyId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setRecommendations(data.recommendations || [])
      }
    } catch (err) {
      console.error('Failed to fetch recommendations:', err)
      setError('Failed to load recommendations')
    } finally {
      setLoading(false)
    }
  }

  const generateRecommendations = async () => {
    if (!selectedProperty) return

    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/tenant-recommendations/ml`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          property_id: selectedProperty,
          space_requirements: {
            size_sq_ft: parseInt(formData.space_size) || 1000,
            industry: formData.industry || 'retail',
            lease_term_months: formData.lease_term_months
          },
          match_criteria: {
            min_credit_score: formData.min_credit_score,
            preferred_industries: [formData.industry]
          }
        })
      })

      if (response.ok) {
        const data = await response.json()
        alert('Recommendations generated successfully!')
        setShowNewForm(false)
        fetchRecommendations(selectedProperty)
      } else {
        throw new Error('Recommendation generation failed')
      }
    } catch (err) {
      console.error('Recommendation generation failed:', err)
      setError('Failed to generate recommendations')
    } finally {
      setLoading(false)
    }
  }

  const selectedPropertyData = properties.find(p => p.id === selectedProperty)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">🎯 Tenant Optimizer</h1>
          <p className="page-subtitle">AI-Powered Tenant Matching & Recommendations</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => setShowNewForm(!showNewForm)}
        >
          {showNewForm ? '❌ Cancel' : '➕ New Recommendation'}
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
              <p><strong>Available Space:</strong> {selectedPropertyData.square_feet?.toLocaleString()} sq ft</p>
            </div>
          )}
        </div>

        {/* Quick Stats */}
        <div className="card">
          <h3 className="card-title">Recommendation Stats</h3>
          <div className="stat-row">
            <span className="stat-label">Total Recommendations:</span>
            <span className="stat-value">{recommendations.length}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Active:</span>
            <span className="stat-value">
              {recommendations.filter(r => r.status === 'active').length}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Avg Confidence:</span>
            <span className="stat-value">
              {recommendations.length > 0
                ? Math.round(
                    recommendations.reduce((sum, r) => sum + (r.confidence_score || 0), 0) / recommendations.length
                  )
                : 0}%
            </span>
          </div>
        </div>
      </div>

      {/* New Recommendation Form */}
      {showNewForm && (
        <div className="card">
          <h3 className="card-title">Generate New Recommendations</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Space Size (sq ft)</label>
              <input
                type="number"
                className="form-input"
                placeholder="1000"
                value={formData.space_size}
                onChange={(e) => setFormData({ ...formData, space_size: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Industry Type</label>
              <select
                className="form-input"
                value={formData.industry}
                onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
              >
                <option value="">Select industry...</option>
                <option value="retail">Retail</option>
                <option value="restaurant">Restaurant</option>
                <option value="office">Office</option>
                <option value="healthcare">Healthcare</option>
                <option value="fitness">Fitness</option>
                <option value="technology">Technology</option>
                <option value="education">Education</option>
              </select>
            </div>
            <div className="form-group">
              <label>Min Credit Score</label>
              <input
                type="number"
                className="form-input"
                value={formData.min_credit_score}
                onChange={(e) => setFormData({ ...formData, min_credit_score: parseInt(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label>Lease Term (months)</label>
              <input
                type="number"
                className="form-input"
                value={formData.lease_term_months}
                onChange={(e) => setFormData({ ...formData, lease_term_months: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={generateRecommendations}
            disabled={loading}
            style={{ marginTop: '1rem' }}
          >
            {loading ? '🔄 Generating...' : '🚀 Generate Recommendations'}
          </button>
        </div>
      )}

      {/* Recommendations List */}
      {recommendations.length > 0 ? (
        <div className="card">
          <h3 className="card-title">Recommended Tenants</h3>
          <div className="recommendations-grid">
            {recommendations.map((rec) => (
              <div key={rec.id} className="recommendation-card">
                <div className="rec-header">
                  <h4>Recommendation #{rec.id}</h4>
                  <span className={`badge badge-${rec.status === 'active' ? 'success' : 'warning'}`}>
                    {rec.status}
                  </span>
                </div>

                <div className="rec-body">
                  <div className="confidence-bar">
                    <div className="confidence-label">
                      Confidence: {rec.confidence_score || 0}%
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${rec.confidence_score || 0}%` }}
                      />
                    </div>
                  </div>

                  {rec.recommended_tenants && rec.recommended_tenants.length > 0 && (
                    <div className="tenants-list">
                      <h5>Top Matches:</h5>
                      {rec.recommended_tenants.slice(0, 3).map((tenant, idx) => (
                        <div key={idx} className="tenant-item">
                          <div className="tenant-info">
                            <strong>{tenant.name || `Tenant ${idx + 1}`}</strong>
                            <span className="tenant-industry">{tenant.industry || 'N/A'}</span>
                          </div>
                          <div className="tenant-score">
                            <span className="badge badge-info">
                              Match: {tenant.match_score || 0}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {rec.space_requirements && (
                    <div className="space-info">
                      <p><strong>Space:</strong> {rec.space_requirements.size_sq_ft} sq ft</p>
                      <p><strong>Industry:</strong> {rec.space_requirements.industry}</p>
                      <p><strong>Term:</strong> {rec.space_requirements.lease_term_months} months</p>
                    </div>
                  )}
                </div>

                <div className="rec-footer">
                  <small>Created: {new Date(rec.created_at).toLocaleDateString()}</small>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        !loading && (
          <div className="card">
            <div className="empty-state">
              <h3>🎯 No Recommendations Yet</h3>
              <p>Click "New Recommendation" to generate AI-powered tenant matches for this property.</p>
            </div>
          </div>
        )
      )}

      {loading && (
        <div className="card">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading recommendations...</p>
          </div>
        </div>
      )}
    </div>
  )
}
