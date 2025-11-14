import { useState, useEffect } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

type ImportType = 'budgets' | 'forecasts' | 'chart-of-accounts' | 'income-statement' | 'balance-sheet'

export default function BulkImport() {
  const [properties, setProperties] = useState<any[]>([])
  const [periods, setPeriods] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null)
  const [importType, setImportType] = useState<ImportType>('budgets')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [formData, setFormData] = useState({
    budget_name: '',
    budget_year: new Date().getFullYear(),
    forecast_name: '',
    forecast_year: new Date().getFullYear(),
    forecast_type: 'annual'
  })

  useEffect(() => {
    fetchProperties()
  }, [])

  useEffect(() => {
    if (selectedProperty) {
      fetchPeriods(selectedProperty)
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

  const downloadTemplate = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/bulk-import/templates/${importType}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${importType}_template.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (err) {
      console.error('Failed to download template:', err)
      setError('Failed to download template')
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setResult(null)
      setError(null)
    }
  }

  const handleImport = async () => {
    if (!file || !selectedProperty || !selectedPeriod) {
      setError('Please select a property, period, and file')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formDataToSend = new FormData()
      formDataToSend.append('file', file)
      formDataToSend.append('property_id', selectedProperty.toString())
      formDataToSend.append('financial_period_id', selectedPeriod.toString())
      formDataToSend.append('created_by', '1')

      if (importType === 'budgets') {
        formDataToSend.append('budget_name', formData.budget_name || 'Imported Budget')
        formDataToSend.append('budget_year', formData.budget_year.toString())
      } else if (importType === 'forecasts') {
        formDataToSend.append('forecast_name', formData.forecast_name || 'Imported Forecast')
        formDataToSend.append('forecast_year', formData.forecast_year.toString())
        formDataToSend.append('forecast_type', formData.forecast_type)
      }

      const response = await fetch(`${API_BASE_URL}/bulk-import/${importType}`, {
        method: 'POST',
        credentials: 'include',
        body: formDataToSend
      })

      if (response.ok) {
        const data = await response.json()
        setResult(data)
        setFile(null)
        if (data.success) {
          alert(`Import completed! ${data.imported_count} records imported successfully.`)
        }
      } else {
        throw new Error('Import failed')
      }
    } catch (err) {
      console.error('Import failed:', err)
      setError('Failed to import data')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">📂 Bulk Data Import</h1>
          <p className="page-subtitle">Import CSV/Excel files for budgets, forecasts, and financial data</p>
        </div>
        <button
          className="btn-secondary"
          onClick={downloadTemplate}
        >
          ⬇️ Download Template
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>⚠️</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {result && result.success && (
        <div className="alert alert-success">
          <span>✅</span>
          <span>
            Successfully imported {result.imported_count} records!
            {result.skipped_count > 0 && ` (${result.skipped_count} skipped)`}
          </span>
          <button onClick={() => setResult(null)}>×</button>
        </div>
      )}

      {/* Import Configuration */}
      <div className="card">
        <h3 className="card-title">Import Configuration</h3>

        <div className="form-grid">
          <div className="form-group">
            <label>Import Type</label>
            <select
              className="form-input"
              value={importType}
              onChange={(e) => setImportType(e.target.value as ImportType)}
            >
              <option value="budgets">Budgets</option>
              <option value="forecasts">Forecasts</option>
              <option value="chart-of-accounts">Chart of Accounts</option>
              <option value="income-statement">Income Statement</option>
              <option value="balance-sheet">Balance Sheet</option>
            </select>
          </div>

          <div className="form-group">
            <label>Property</label>
            <select
              className="form-input"
              value={selectedProperty || ''}
              onChange={(e) => setSelectedProperty(Number(e.target.value))}
            >
              <option value="">Select property...</option>
              {properties.map(p => (
                <option key={p.id} value={p.id}>
                  {p.property_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Financial Period</label>
            <select
              className="form-input"
              value={selectedPeriod || ''}
              onChange={(e) => setSelectedPeriod(Number(e.target.value))}
            >
              <option value="">Select period...</option>
              {periods.map(p => (
                <option key={p.id} value={p.id}>
                  {p.period_name}
                </option>
              ))}
            </select>
          </div>

          {importType === 'budgets' && (
            <>
              <div className="form-group">
                <label>Budget Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Annual Budget 2024"
                  value={formData.budget_name}
                  onChange={(e) => setFormData({ ...formData, budget_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Budget Year</label>
                <input
                  type="number"
                  className="form-input"
                  value={formData.budget_year}
                  onChange={(e) => setFormData({ ...formData, budget_year: parseInt(e.target.value) })}
                />
              </div>
            </>
          )}

          {importType === 'forecasts' && (
            <>
              <div className="form-group">
                <label>Forecast Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Q1 Forecast 2024"
                  value={formData.forecast_name}
                  onChange={(e) => setFormData({ ...formData, forecast_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Forecast Year</label>
                <input
                  type="number"
                  className="form-input"
                  value={formData.forecast_year}
                  onChange={(e) => setFormData({ ...formData, forecast_year: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>Forecast Type</label>
                <select
                  className="form-input"
                  value={formData.forecast_type}
                  onChange={(e) => setFormData({ ...formData, forecast_type: e.target.value })}
                >
                  <option value="annual">Annual</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </>
          )}
        </div>
      </div>

      {/* File Upload */}
      <div className="card">
        <h3 className="card-title">Upload File</h3>
        <div className="upload-area">
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            className="file-input"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="upload-label">
            {file ? (
              <>
                <div className="file-icon">📄</div>
                <div className="file-name">{file.name}</div>
                <div className="file-size">{(file.size / 1024).toFixed(2)} KB</div>
              </>
            ) : (
              <>
                <div className="upload-icon">⬆️</div>
                <div className="upload-text">Click to upload or drag and drop</div>
                <div className="upload-hint">CSV, XLSX, or XLS files</div>
              </>
            )}
          </label>
        </div>

        <button
          className="btn-primary"
          onClick={handleImport}
          disabled={loading || !file}
          style={{ marginTop: '1rem' }}
        >
          {loading ? '🔄 Importing...' : '🚀 Import Data'}
        </button>
      </div>

      {/* Import Results */}
      {result && (
        <div className="card">
          <h3 className="card-title">Import Results</h3>
          <div className="result-stats">
            <div className="result-stat">
              <div className="stat-value">{result.imported_count || 0}</div>
              <div className="stat-label">Records Imported</div>
            </div>
            <div className="result-stat">
              <div className="stat-value">{result.skipped_count || 0}</div>
              <div className="stat-label">Records Skipped</div>
            </div>
            <div className="result-stat">
              <div className="stat-value">{result.total_rows || 0}</div>
              <div className="stat-label">Total Rows</div>
            </div>
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="errors-section">
              <h4>Errors:</h4>
              <ul className="error-list">
                {result.errors.map((error: string, idx: number) => (
                  <li key={idx} className="error-item">
                    <span className="error-icon">⚠️</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.warnings && result.warnings.length > 0 && (
            <div className="warnings-section">
              <h4>Warnings:</h4>
              <ul className="warning-list">
                {result.warnings.map((warning: string, idx: number) => (
                  <li key={idx} className="warning-item">
                    <span className="warning-icon">⚡</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Supported Formats */}
      <div className="card">
        <h3 className="card-title">Supported Import Types</h3>
        <div className="import-types-grid">
          <div className="import-type-card">
            <h4>📋 Budgets</h4>
            <p>Import budget data with account codes, amounts, and tolerance settings</p>
          </div>
          <div className="import-type-card">
            <h4>📊 Forecasts</h4>
            <p>Import forecast projections by account and period</p>
          </div>
          <div className="import-type-card">
            <h4>📑 Chart of Accounts</h4>
            <p>Bulk import account structures and hierarchies</p>
          </div>
          <div className="import-type-card">
            <h4>💰 Income Statement</h4>
            <p>Import revenue and expense data by period</p>
          </div>
          <div className="import-type-card">
            <h4>🏦 Balance Sheet</h4>
            <p>Import assets, liabilities, and equity data</p>
          </div>
        </div>
      </div>
    </div>
  )
}
