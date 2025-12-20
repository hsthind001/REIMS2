import { useState, useEffect, useRef } from 'react'
import '../App.css'
import { useAuth } from '../components/AuthContext'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1'

interface QueryResult {
  id: number
  query_text: string
  natural_language_result: string
  sql_query: string
  result_data: any
  confidence_score: number
  execution_time_ms: number
  created_at: string
  status: string
}

export default function NaturalLanguageQuery() {
  const { user, isAuthenticated } = useAuth()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<QueryResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSQL, setShowSQL] = useState(false)
  const queryInputRef = useRef<HTMLTextAreaElement>(null)

  // Example queries
  const exampleQueries = [
    "What is the total NOI for all properties in 2024?",
    "Show me properties with DSCR below 1.25",
    "Which properties have the highest occupancy rate?",
    "What is the average cap rate across all retail properties?",
    "List properties with rent growth above 5% last year",
    "Show me all properties in California with NOI over $1M",
    "What are the top 3 performing properties by NOI?",
    "Which tenants are expiring in the next 6 months?"
  ]

  useEffect(() => {
    fetchRecentQueries()
  }, [])

  const fetchRecentQueries = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/queries/recent?limit=10`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setResults(data.queries || [])
      }
    } catch (err) {
      console.error('Failed to fetch recent queries:', err)
    }
  }

  const executeQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    // Check authentication
    if (!isAuthenticated || !user) {
      setError('Please log in to use Natural Language Query')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/nlq/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          query_text: query,
          user_id: user.id // Use actual user ID from auth context
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Add to beginning of results
          setResults([data.result, ...results])
          setQuery('')
        } else {
          setError(data.error || 'Query failed')
        }
      } else {
        throw new Error('Query execution failed')
      }
    } catch (err) {
      console.error('Query failed:', err)
      setError('Failed to execute query')
    } finally {
      setLoading(false)
    }
  }

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery)
    queryInputRef.current?.focus()
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      executeQuery()
    }
  }

  const formatResultData = (data: any) => {
    if (!data) return null

    if (Array.isArray(data)) {
      if (data.length === 0) return <p className="text-muted">No results found</p>

      // Table format for arrays
      return (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                {Object.keys(data[0]).map((key) => (
                  <th key={key}>{key.replace(/_/g, ' ').toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx}>
                  {Object.values(row).map((value: any, vidx) => (
                    <td key={vidx}>
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    // Object format
    return (
      <div className="data-grid">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="data-item">
            <span className="data-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
            <span className="data-value">
              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
            </span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">💬 Natural Language Query</h1>
          <p className="page-subtitle">Ask questions about your properties in plain English</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Query Input */}
      <div className="card query-card">
        <h3 className="card-title">Ask a Question</h3>
        <div className="query-input-container">
          <textarea
            ref={queryInputRef}
            className="query-input"
            placeholder="e.g., What is the total NOI for all properties in 2024?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            rows={3}
          />
          <div className="query-actions">
            <small className="text-muted">Press Cmd+Enter or Ctrl+Enter to execute</small>
            <button
              className="btn-primary"
              onClick={executeQuery}
              disabled={loading || !query.trim()}
            >
              {loading ? '🔄 Processing...' : '🚀 Execute Query'}
            </button>
          </div>
        </div>

        {/* Example Queries */}
        <div className="examples-section">
          <h4>Example Queries:</h4>
          <div className="examples-grid">
            {exampleQueries.map((example, idx) => (
              <button
                key={idx}
                className="example-chip"
                onClick={() => handleExampleClick(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Query Results */}
      <div className="results-section">
        <h3 className="section-title">
          {results.length > 0 ? 'Query Results' : 'Recent Queries'}
        </h3>

        {results.length === 0 && !loading && (
          <div className="card">
            <div className="empty-state">
              <h3>💡 Get Started</h3>
              <p>Type a question above or click an example query to see instant results.</p>
            </div>
          </div>
        )}

        {results.map((result) => (
          <div key={result.id} className="card result-card">
            {/* Query Header */}
            <div className="result-header">
              <div className="query-text">
                <strong>Q:</strong> {result.query_text}
              </div>
              <div className="query-meta">
                <span className={`badge badge-${result.status === 'completed' ? 'success' : 'warning'}`}>
                  {result.status}
                </span>
                <span className="badge badge-info">
                  {result.confidence_score || 0}% confidence
                </span>
                <span className="text-muted">
                  {result.execution_time_ms}ms
                </span>
              </div>
            </div>

            {/* Natural Language Answer */}
            {result.natural_language_result && (
              <div className="nl-answer">
                <strong>Answer:</strong>
                <p>{result.natural_language_result}</p>
              </div>
            )}

            {/* Result Data */}
            {result.result_data && (
              <div className="result-data">
                {formatResultData(result.result_data)}
              </div>
            )}

            {/* SQL Query (Expandable) */}
            <div className="sql-section">
              <button
                className="sql-toggle"
                onClick={() => setShowSQL(!showSQL)}
              >
                {showSQL ? '▼' : '▶'} View SQL Query
              </button>
              {showSQL && result.sql_query && (
                <pre className="sql-code">
                  <code>{result.sql_query}</code>
                </pre>
              )}
            </div>

            {/* Footer */}
            <div className="result-footer">
              <small>Executed: {new Date(result.created_at).toLocaleString()}</small>
            </div>
          </div>
        ))}
      </div>

      {loading && (
        <div className="card">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Executing your query...</p>
          </div>
        </div>
      )}
    </div>
  )
}
