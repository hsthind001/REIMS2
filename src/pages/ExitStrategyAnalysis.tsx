import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1'

interface ExitStrategy {
  strategy: string
  irr: number
  npv: number
  total_return: number
  annual_cashflow: number
  terminal_value: number
  recommendation_score: number
}

interface ExitAnalysis {
  property_id: number
  investment_amount: number
  holding_period_years: number
  discount_rate: number
  strategies: {
    hold: ExitStrategy
    refinance: ExitStrategy
    sale: ExitStrategy
  }
  recommended_strategy: string
  sensitivity_analysis: any
}

export default function ExitStrategyAnalysis() {
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [analysis, setAnalysis] = useState<ExitAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    investment_amount: 10000000,
    holding_period_years: 5,
    discount_rate: 0.10
  })

  useEffect(() => {
    fetchProperties()
  }, [])

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

  const analyzeExitStrategies = async () => {
    if (!selectedProperty) {
      setError('Please select a property')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/properties/${selectedProperty}/exit-strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          investment_amount: formData.investment_amount,
          holding_period_years: formData.holding_period_years,
          discount_rate: formData.discount_rate
        })
      })

      if (response.ok) {
        const data = await response.json()
        setAnalysis(data)
      } else {
        throw new Error('Analysis failed')
      }
    } catch (err) {
      console.error('Exit strategy analysis failed:', err)
      setError('Failed to analyze exit strategies')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return (value * 100).toFixed(2) + '%'
  }

  const getStrategyColor = (strategy: string, recommended: string) => {
    return strategy === recommended ? 'success' : 'info'
  }

  const selectedPropertyData = properties.find(p => p.id === selectedProperty)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">🎯 Exit Strategy Analysis</h1>
          <p className="page-subtitle">IRR & NPV Analysis for Investment Exit Strategies</p>
        </div>
        <button
          className="btn-primary"
          onClick={analyzeExitStrategies}
          disabled={loading || !selectedProperty}
        >
          {loading ? '🔄 Analyzing...' : '📊 Run Analysis'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Configuration */}
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
                {p.property_name}{p.address ? ` - ${p.address}` : ''}
              </option>
            ))}
          </select>

          {selectedPropertyData && (
            <div className="property-card" style={{ marginTop: '1rem' }}>
              <h4>{selectedPropertyData.property_name}</h4>
              {selectedPropertyData.address && <p><strong>Address:</strong> {selectedPropertyData.address}</p>}
              <p><strong>Type:</strong> {selectedPropertyData.property_type}</p>
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="card-title">Analysis Parameters</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Investment Amount ($)</label>
              <input
                type="number"
                className="form-input"
                value={formData.investment_amount}
                onChange={(e) => setFormData({ ...formData, investment_amount: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label>Holding Period (Years)</label>
              <input
                type="number"
                className="form-input"
                value={formData.holding_period_years}
                onChange={(e) => setFormData({ ...formData, holding_period_years: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label>Discount Rate (%)</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.discount_rate * 100}
                onChange={(e) => setFormData({ ...formData, discount_rate: Number(e.target.value) / 100 })}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <>
          {/* Recommended Strategy */}
          <div className="card">
            <h3 className="card-title">Recommended Strategy</h3>
            <div className="recommendation-banner">
              <div className="rec-icon">
                {analysis.recommended_strategy === 'hold' && '🏢'}
                {analysis.recommended_strategy === 'refinance' && '💰'}
                {analysis.recommended_strategy === 'sale' && '💵'}
              </div>
              <div className="rec-content">
                <h2 style={{ textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  {analysis.recommended_strategy}
                </h2>
                <p>Based on IRR and NPV analysis across all strategies</p>
              </div>
            </div>
          </div>

          {/* Strategy Comparison */}
          <div className="strategies-grid">
            {/* Hold Strategy */}
            <div className={`strategy-card ${analysis.recommended_strategy === 'hold' ? 'recommended' : ''}`}>
              <div className="strategy-header">
                <div className="strategy-icon">🏢</div>
                <div>
                  <h3>Hold Strategy</h3>
                  <p className="strategy-desc">Continue operating the property</p>
                </div>
              </div>

              {analysis.strategies.hold && (
                <div className="strategy-metrics">
                  <div className="metric-row">
                    <span className="metric-label">IRR:</span>
                    <span className="metric-value">{formatPercent(analysis.strategies.hold.irr)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">NPV:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.hold.npv)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Total Return:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.hold.total_return)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Annual Cash Flow:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.hold.annual_cashflow)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Terminal Value:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.hold.terminal_value)}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Refinance Strategy */}
            <div className={`strategy-card ${analysis.recommended_strategy === 'refinance' ? 'recommended' : ''}`}>
              <div className="strategy-header">
                <div className="strategy-icon">💰</div>
                <div>
                  <h3>Refinance Strategy</h3>
                  <p className="strategy-desc">Refinance and extract equity</p>
                </div>
              </div>

              {analysis.strategies.refinance && (
                <div className="strategy-metrics">
                  <div className="metric-row">
                    <span className="metric-label">IRR:</span>
                    <span className="metric-value">{formatPercent(analysis.strategies.refinance.irr)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">NPV:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.refinance.npv)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Total Return:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.refinance.total_return)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Annual Cash Flow:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.refinance.annual_cashflow)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Terminal Value:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.refinance.terminal_value)}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Sale Strategy */}
            <div className={`strategy-card ${analysis.recommended_strategy === 'sale' ? 'recommended' : ''}`}>
              <div className="strategy-header">
                <div className="strategy-icon">💵</div>
                <div>
                  <h3>Sale Strategy</h3>
                  <p className="strategy-desc">Sell the property now</p>
                </div>
              </div>

              {analysis.strategies.sale && (
                <div className="strategy-metrics">
                  <div className="metric-row">
                    <span className="metric-label">IRR:</span>
                    <span className="metric-value">{formatPercent(analysis.strategies.sale.irr)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">NPV:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.sale.npv)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Total Return:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.sale.total_return)}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Sale Price:</span>
                    <span className="metric-value">{formatCurrency(analysis.strategies.sale.terminal_value)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Investment Summary */}
          <div className="card">
            <h3 className="card-title">Investment Summary</h3>
            <div className="data-grid">
              <div className="data-item">
                <span className="data-label">INITIAL INVESTMENT:</span>
                <span className="data-value">{formatCurrency(analysis.investment_amount)}</span>
              </div>
              <div className="data-item">
                <span className="data-label">HOLDING PERIOD:</span>
                <span className="data-value">{analysis.holding_period_years} years</span>
              </div>
              <div className="data-item">
                <span className="data-label">DISCOUNT RATE:</span>
                <span className="data-value">{formatPercent(analysis.discount_rate)}</span>
              </div>
              <div className="data-item">
                <span className="data-label">BEST IRR:</span>
                <span className="data-value">
                  {formatPercent(Math.max(
                    analysis.strategies.hold.irr,
                    analysis.strategies.refinance.irr,
                    analysis.strategies.sale.irr
                  ))}
                </span>
              </div>
            </div>
          </div>
        </>
      )}

      {loading && (
        <div className="card">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Analyzing exit strategies...</p>
          </div>
        </div>
      )}

      {!analysis && !loading && (
        <div className="card">
          <div className="empty-state">
            <h3>📊 Ready to Analyze</h3>
            <p>Select a property and configure parameters, then click "Run Analysis" to evaluate exit strategies.</p>
          </div>
        </div>
      )}
    </div>
  )
}
