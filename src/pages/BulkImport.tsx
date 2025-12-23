import { useState, useEffect } from 'react'
import '../App.css'
import { propertyService } from '../lib/property'

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1'

interface FileWithMetadata {
  file: File
  detectedType: string
  status: 'pending' | 'uploading' | 'success' | 'skipped' | 'replaced' | 'error'
  uploadId?: number
  error?: string
  message?: string
  month?: number
  fileType?: string
  warning?: string
  anomalies?: string[]
}

// Detect document type from filename (frontend version)
const detectDocumentTypeFromFilename = (filename: string): string => {
  const filenameLower = filename.toLowerCase()
  
  // Balance Sheet patterns
  if (filenameLower.includes('balance') && filenameLower.includes('sheet')) {
    return 'balance_sheet'
  }
  if (filenameLower.includes('balance') || filenameLower.match(/\bbs\b/)) {
    return 'balance_sheet'
  }
  
  // Income Statement patterns
  if (filenameLower.includes('income') && filenameLower.includes('statement')) {
    return 'income_statement'
  }
  if (filenameLower.includes('income') || filenameLower.includes('p&l') || 
      filenameLower.includes('profit') && filenameLower.includes('loss')) {
    return 'income_statement'
  }
  
  // Cash Flow patterns
  if (filenameLower.includes('cash') && filenameLower.includes('flow')) {
    return 'cash_flow'
  }
  if (filenameLower.match(/\bcf\b/) || filenameLower.includes('cashflow')) {
    return 'cash_flow'
  }
  
  // Rent Roll patterns
  if (filenameLower.includes('rent') && filenameLower.includes('roll')) {
    return 'rent_roll'
  }
  if (filenameLower.includes('rentroll') || 
      (filenameLower.includes('lease') && filenameLower.includes('roll'))) {
    return 'rent_roll'
  }
  
  // Mortgage Statement patterns (matching backend patterns)
  if (filenameLower.includes('mortgage') && filenameLower.includes('statement')) {
    return 'mortgage_statement'
  }
  if (filenameLower.match(/\bmortgage\b/) || filenameLower.includes('mortgage stmt')) {
    return 'mortgage_statement'
  }
  if (filenameLower.includes('loan') && filenameLower.includes('statement')) {
    return 'mortgage_statement'
  }
  // Escrow patterns (common in mortgage statements)
  if (filenameLower.includes('escrow') && (filenameLower.includes('statement') || filenameLower.includes('loan') || filenameLower.includes('pdf'))) {
    return 'mortgage_statement'
  }
  if (filenameLower.includes('loan') && filenameLower.includes('escrow')) {
    return 'mortgage_statement'
  }
  // Lender names with loan/escrow (Wells Fargo, CIBC, NorthMarq, etc.)
  const mortgageLenders = ['wells fargo', 'cibc', 'northmarq', 'chase', 'bank of america', 'citibank', 'us bank', 'pnc', 'td bank']
  if (mortgageLenders.some(lender => filenameLower.includes(lender)) && (filenameLower.includes('loan') || filenameLower.includes('escrow') || filenameLower.includes('statement'))) {
    return 'mortgage_statement'
  }
  // Loan with number pattern (e.g., "loan 1008")
  if (filenameLower.includes('loan') && filenameLower.match(/\d{4,}/)) {
    return 'mortgage_statement'
  }
  // Escrow with number pattern
  if (filenameLower.includes('escrow') && filenameLower.match(/\d{4,}/)) {
    return 'mortgage_statement'
  }
  
  return 'unknown'
}

export default function BulkImport() {
  const [properties, setProperties] = useState<any[]>([])
  const [selectedProperty, setSelectedProperty] = useState<string>('')
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear())
  const [duplicateStrategy, setDuplicateStrategy] = useState<string>('skip')
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('all')
  const [files, setFiles] = useState<FileWithMetadata[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [showMonitoring, setShowMonitoring] = useState(false)
  const [monitoringData, setMonitoringData] = useState<any>(null)
  const [monitoringInterval, setMonitoringInterval] = useState<NodeJS.Timeout | null>(null)

  useEffect(() => {
    fetchProperties()
  }, [])

  const fetchProperties = async () => {
    try {
      // Use propertyService which handles authentication properly
      const props = await propertyService.getAllProperties()
      
      // Filter out inactive properties and sort intelligently
      const filteredProps = props
        .filter((p: any) => p.status !== 'inactive' && p.status !== 'deleted')
        .sort((a: any, b: any) => {
          // Sort by property_code if available, otherwise by name
          if (a.property_code && b.property_code) {
            return a.property_code.localeCompare(b.property_code)
          }
          if (a.property_name && b.property_name) {
            return a.property_name.localeCompare(b.property_name)
          }
          return 0
        })
      
      setProperties(filteredProps)
      
      if (props.length > 0) {
        // Intelligently select the first property with a code, or just the first one
        const propWithCode = props.find((p: any) => p.property_code) || props[0]
        // Prefer property_code, fallback to id as string
        const selectedValue = propWithCode.property_code || propWithCode.id?.toString() || ''
        setSelectedProperty(selectedValue)
      } else {
        setError('No properties found. Please create a property first.')
      }
    } catch (err: any) {
      console.error('Failed to fetch properties:', err)
      setError(`Failed to load properties: ${err.message || 'Network error'}`)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles: FileWithMetadata[] = Array.from(e.target.files).map(file => ({
        file,
        detectedType: detectDocumentTypeFromFilename(file.name),
        status: 'pending' as const
      }))
      setFiles(prev => [...prev, ...newFiles])
      setResult(null)
      setError(null)
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleBulkUpload = async () => {
    // Validation
    if (files.length === 0) {
      setError('Please select at least one file to upload')
      return
    }
    
    if (!selectedProperty) {
      setError('Please select a property')
      return
    }
    
    // Intelligently find property by code or id
    const property = properties.find((p: any) => {
      const propCode = p.property_code || p.code || ''
      const propId = p.id?.toString() || ''
      return propCode === selectedProperty || propId === selectedProperty
    })
    
    if (!property) {
      setError('Selected property not found. Please select a valid property.')
      return
    }
    
    // Get property code - prefer property_code, fallback to code, then id
    const propertyCode = property.property_code || property.code || property.id?.toString()
    
    if (!propertyCode) {
      setError('Property code not found. Please select a property with a valid code.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    
    // Update all files to uploading status
    setFiles(prev => prev.map(f => ({ ...f, status: 'uploading' as const })))

    try {
      const formData = new FormData()
      formData.append('property_code', propertyCode)
      formData.append('year', selectedYear.toString())
      formData.append('duplicate_strategy', duplicateStrategy)

      // Append all files - FastAPI expects all files with the same field name 'files'
      files.forEach(fileWithMeta => {
        formData.append('files', fileWithMeta.file, fileWithMeta.file.name)
      })

      console.log('Uploading to:', `${API_BASE_URL}/documents/bulk-upload`)
      console.log('Property code:', propertyCode)
      console.log('Year:', selectedYear)
      console.log('Files count:', files.length)
      
      const response = await fetch(`${API_BASE_URL}/documents/bulk-upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      })
      
      console.log('Response status:', response.status, response.statusText)
      console.log('Response URL:', response.url)

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`
        
        // Try to get detailed error from response
        try {
          const contentType = response.headers.get('content-type')
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json()
            errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage
            if (typeof errorMessage === 'object') {
              errorMessage = JSON.stringify(errorMessage, null, 2)
            }
          } else {
            // Try to read as text for non-JSON errors
            const textError = await response.text()
            if (textError) {
              errorMessage = textError.length > 200 ? textError.substring(0, 200) + '...' : textError
            }
          }
        } catch (e) {
          console.error('Failed to parse error response:', e)
          // Keep the default error message
        }
        
        // Provide helpful error messages for common status codes
        if (response.status === 404) {
          errorMessage = `Endpoint not found. Please ensure the backend is running and the endpoint /documents/bulk-upload is available. ${errorMessage}`
        } else if (response.status === 400) {
          errorMessage = `Bad request: ${errorMessage}. Please check your file selection and property/year settings.`
        } else if (response.status === 500) {
          errorMessage = `Server error: ${errorMessage}. Please check the backend logs for details.`
        }
        
        setError(errorMessage)
        setFiles(prev => prev.map(f => ({ ...f, status: 'error' as const, error: errorMessage })))
        return
      }

      const data = await response.json()
      setResult(data)
      
      // Update file statuses based on results
      if (data.results && Array.isArray(data.results)) {
        setFiles(prev => prev.map((fileWithMeta, index) => {
          const result = data.results.find((r: any) => r.filename === fileWithMeta.file.name)
          if (result) {
            return {
              ...fileWithMeta,
              status: result.status || 'error',
              uploadId: result.upload_id,
              message: result.message,
              error: result.error,
              month: result.month,
              fileType: result.file_type,
              warning: result.warning,
              anomalies: result.anomalies
            }
          }
          return fileWithMeta
        }))
      }
      
      if (data.success) {
        // Clear files after successful upload
        setTimeout(() => {
          setFiles([])
        }, 3000)
      }
    } catch (err: any) {
      console.error('Bulk upload failed:', err)
      const errorMessage = err.message || 'Failed to upload files. Please check your connection and try again.'
      setError(errorMessage)
      setFiles(prev => prev.map(f => ({ ...f, status: 'error' as const, error: errorMessage })))
    } finally {
      setLoading(false)
    }
  }

  const fetchMonitoringData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/monitoring-status`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setMonitoringData(data)
      }
    } catch (err) {
      console.error('Failed to fetch monitoring data:', err)
    }
  }

  const startMonitoring = () => {
    setShowMonitoring(true)
    fetchMonitoringData()
    // Refresh every 10 seconds
    const interval = setInterval(fetchMonitoringData, 10000)
    setMonitoringInterval(interval)
  }

  const stopMonitoring = () => {
    setShowMonitoring(false)
    if (monitoringInterval) {
      clearInterval(monitoringInterval)
      setMonitoringInterval(null)
    }
  }

  useEffect(() => {
    // Cleanup interval on unmount
    return () => {
      if (monitoringInterval) {
        clearInterval(monitoringInterval)
      }
    }
  }, [monitoringInterval])

  const getDocumentTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      'balance_sheet': 'Balance Sheet',
      'income_statement': 'Income Statement',
      'cash_flow': 'Cash Flow',
      'rent_roll': 'Rent Roll',
      'mortgage_statement': 'Mortgage Statement',
      'unknown': 'Unknown'
    }
    return labels[type] || type
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <span style={{ color: 'green', fontWeight: 'bold' }}>✅ Success</span>
      case 'replaced':
        return <span style={{ color: 'orange', fontWeight: 'bold' }}>🔄 Replaced</span>
      case 'skipped':
        return <span style={{ color: 'blue', fontWeight: 'bold' }}>⏭️ Skipped</span>
      case 'error':
        return <span style={{ color: 'red', fontWeight: 'bold' }}>❌ Failed</span>
      case 'uploading':
        return <span style={{ color: 'blue', fontWeight: 'bold' }}>🔄 Uploading...</span>
      default:
        return <span style={{ color: 'gray' }}>⏳ Pending</span>
    }
  }

  // Filter files based on selected document type
  const filteredFiles = fileTypeFilter === 'all'
    ? files
    : files.filter(f => f.detectedType === fileTypeFilter)

  return (
    <div className="page-container">
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
              <button
                className="btn-secondary"
                onClick={() => window.location.hash = ''}
                style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
              >
                ← Back to Data Control Center
              </button>
            </div>
            <h1 className="page-title">📂 Bulk Document Upload</h1>
            <p className="page-subtitle">Upload multiple documents (PDF, CSV, Excel, DOC) for a selected year. Document types are auto-detected from filenames.</p>
          </div>
          <button
            className="btn btn-primary"
            onClick={showMonitoring ? stopMonitoring : startMonitoring}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              fontSize: '0.9rem',
              marginLeft: '1rem',
              whiteSpace: 'nowrap'
            }}
          >
            {showMonitoring ? (
              <>
                <span>⏸️</span>
                <span>Stop Monitoring</span>
              </>
            ) : (
              <>
                <span>📊</span>
                <span>Start Monitoring</span>
              </>
            )}
          </button>
        </div>
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
            Successfully uploaded {result.uploaded} of {result.total_files} files!
            {result.failed > 0 && ` (${result.failed} failed)`}
          </span>
          <button onClick={() => setResult(null)}>×</button>
        </div>
      )}

      {/* Upload Configuration */}
      <div className="card">
        <h3 className="card-title">Upload Configuration</h3>

        <div className="form-grid">
          <div className="form-group">
            <label>Property *</label>
            <select
              className="form-input"
              value={selectedProperty}
              onChange={(e) => setSelectedProperty(e.target.value)}
              disabled={loading || properties.length === 0}
            >
              <option value="">
                {properties.length === 0 ? 'Loading properties...' : 'Select property...'}
              </option>
              {properties.map(p => {
                const displayName = p.property_name || p.name || `Property ${p.id}`
                const code = p.property_code || p.code || ''
                const city = p.city || ''
                const value = p.property_code || p.code || p.id?.toString() || ''
                
                // Create intelligent display: "Property Name (CODE) - City" or just "Property Name (CODE)"
                let displayText = displayName
                if (code) {
                  displayText += ` (${code})`
                }
                if (city) {
                  displayText += ` - ${city}`
                }
                
                return (
                  <option key={p.id || value} value={value}>
                    {displayText}
                  </option>
                )
              })}
            </select>
            {properties.length === 0 && !loading && (
              <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                No properties available. Please create a property first.
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Year *</label>
            <input
              type="number"
              className="form-input"
              value={selectedYear}
              onChange={(e) => setSelectedYear(parseInt(e.target.value) || new Date().getFullYear())}
              min="2000"
              max="2100"
            />
          </div>

          <div className="form-group">
            <label>If Duplicate Documents Exist *</label>
            <select
              className="form-input"
              value={duplicateStrategy}
              onChange={(e) => setDuplicateStrategy(e.target.value)}
              disabled={loading}
            >
              <option value="skip">Skip - Keep existing documents</option>
              <option value="replace">Replace - Overwrite with new files</option>
            </select>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
              {duplicateStrategy === 'skip' && '⏭️ Existing documents will be preserved'}
              {duplicateStrategy === 'replace' && '⚠️ Existing documents will be deleted and replaced'}
            </div>
          </div>

          <div className="form-group">
            <label>Filter by Document Type</label>
            <select
              className="form-input"
              value={fileTypeFilter}
              onChange={(e) => setFileTypeFilter(e.target.value)}
              disabled={loading}
            >
              <option value="all">All Document Types</option>
              <option value="balance_sheet">Balance Sheet Only</option>
              <option value="income_statement">Income Statement Only</option>
              <option value="cash_flow">Cash Flow Only</option>
              <option value="rent_roll">Rent Roll Only</option>
              <option value="mortgage_statement">Mortgage Statement Only</option>
            </select>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
              {fileTypeFilter === 'all' ? '📄 All files will be shown' : `📊 Only ${fileTypeFilter.replace('_', ' ')} files will be shown`}
            </div>
          </div>
        </div>
      </div>

      {/* File Upload */}
      <div className="card">
        <h3 className="card-title">Select Files</h3>
        <div className="upload-area">
          <input
            type="file"
            accept=".pdf,.csv,.xlsx,.xls,.doc,.docx"
            multiple
            onChange={handleFileChange}
            className="file-input"
            id="file-upload"
            disabled={loading}
          />
          <label htmlFor="file-upload" className="upload-label">
            <div className="upload-icon">⬆️</div>
            <div className="upload-text">Click to select files or drag and drop</div>
            <div className="upload-hint">PDF, CSV, Excel (.xlsx, .xls), DOC (.doc, .docx)</div>
            <div className="upload-hint" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
              You can select multiple files at once (Ctrl+Click or Cmd+Click)
            </div>
          </label>
        </div>

        {files.length > 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            <h4 style={{ marginBottom: '1rem' }}>
              Selected Files ({filteredFiles.length}{files.length !== filteredFiles.length ? ` of ${files.length}` : ''}):
            </h4>
            <div style={{ 
              border: '1px solid #ddd', 
              borderRadius: '4px', 
              padding: '1rem',
              maxHeight: '400px',
              overflowY: 'auto'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd' }}>
                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Filename</th>
                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Detected Type</th>
                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Size</th>
                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Status</th>
                    <th style={{ textAlign: 'center', padding: '0.5rem' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiles.map((fileWithMeta, index) => (
                    <tr key={index} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '0.5rem' }}>{fileWithMeta.file.name}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          backgroundColor: fileWithMeta.detectedType === 'unknown' ? '#ffebee' : '#e3f2fd',
                          color: fileWithMeta.detectedType === 'unknown' ? '#c62828' : '#1565c0',
                          fontSize: '0.85rem'
                        }}>
                          {getDocumentTypeLabel(fileWithMeta.detectedType)}
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {(fileWithMeta.file.size / 1024).toFixed(2)} KB
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {getStatusBadge(fileWithMeta.status)}
                        {fileWithMeta.warning && (
                          <div style={{ fontSize: '0.8rem', color: '#ff9800', marginTop: '0.25rem', display: 'flex', alignItems: 'flex-start', gap: '0.25rem' }}>
                            <span>⚠️</span>
                            <span>{fileWithMeta.warning}</span>
                          </div>
                        )}
                        {fileWithMeta.anomalies && fileWithMeta.anomalies.length > 0 && (
                          <div style={{ fontSize: '0.8rem', color: '#f57c00', marginTop: '0.25rem' }}>
                            {fileWithMeta.anomalies.map((anomaly, idx) => (
                              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.25rem', marginTop: idx > 0 ? '0.15rem' : 0 }}>
                                <span>🔍</span>
                                <span>{anomaly}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {fileWithMeta.error && (
                          <div style={{ fontSize: '0.8rem', color: 'red', marginTop: '0.25rem' }}>
                            {fileWithMeta.error}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                        {fileWithMeta.status === 'pending' && (
                          <button
                            onClick={() => removeFile(index)}
                            style={{
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#f44336',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer'
                            }}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <button
          className="btn-primary"
          onClick={handleBulkUpload}
          disabled={loading || files.length === 0 || !selectedProperty}
          style={{ marginTop: '1rem' }}
        >
          {loading ? '🔄 Uploading...' : `🚀 Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
        </button>
      </div>

      {/* Upload Results */}
      {result && (
        <div className="card">
          <h3 className="card-title">Upload Results</h3>
          <div className="result-stats">
            <div className="result-stat">
              <div className="stat-value">{result.uploaded || 0}</div>
              <div className="stat-label">New Uploads</div>
            </div>
            {(result.replaced || 0) > 0 && (
              <div className="result-stat">
                <div className="stat-value" style={{ color: 'orange' }}>{result.replaced}</div>
                <div className="stat-label">Replaced</div>
              </div>
            )}
            {(result.skipped || 0) > 0 && (
              <div className="result-stat">
                <div className="stat-value" style={{ color: 'blue' }}>{result.skipped}</div>
                <div className="stat-label">Skipped</div>
              </div>
            )}
            <div className="result-stat">
              <div className="stat-value" style={{ color: result.failed > 0 ? 'red' : 'inherit' }}>{result.failed || 0}</div>
              <div className="stat-label">Failed</div>
            </div>
            <div className="result-stat">
              <div className="stat-value">{result.total_files || 0}</div>
              <div className="stat-label">Total Files</div>
            </div>
          </div>
          {(result.duplicates_found || 0) > 0 && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#f0f9ff', borderRadius: '4px', fontSize: '0.9rem' }}>
              ℹ️ Found {result.duplicates_found} duplicate document{result.duplicates_found > 1 ? 's' : ''} (Strategy: <strong>{result.duplicate_strategy}</strong>)
            </div>
          )}

          {result.results && result.results.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h4>File Details:</h4>
              <div style={{ 
                border: '1px solid #ddd', 
                borderRadius: '4px', 
                padding: '1rem',
                maxHeight: '300px',
                overflowY: 'auto'
              }}>
                {result.results.map((fileResult: any, index: number) => (
                  <div key={index} style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    backgroundColor: fileResult.status === 'success' ? '#e8f5e9' : '#ffebee',
                    borderRadius: '4px',
                    borderLeft: fileResult.anomalies && fileResult.anomalies.length > 0 ? '4px solid #ff9800' : 'none'
                  }}>
                    <div style={{ fontWeight: 'bold' }}>{fileResult.filename}</div>
                    <div style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
                      Type: {getDocumentTypeLabel(fileResult.document_type)} |
                      Month: {fileResult.month || 'N/A'} |
                      File Type: {fileResult.file_type || 'N/A'} |
                      Status: {fileResult.status === 'success' ? '✅ Success' : '❌ Failed'}
                    </div>
                    {fileResult.warning && (
                      <div style={{ fontSize: '0.85rem', color: '#ff9800', marginTop: '0.5rem', padding: '0.5rem', backgroundColor: '#fff3e0', borderRadius: '4px' }}>
                        <strong>⚠️ Warning:</strong> {fileResult.warning}
                      </div>
                    )}
                    {fileResult.anomalies && fileResult.anomalies.length > 0 && (
                      <div style={{ fontSize: '0.85rem', color: '#f57c00', marginTop: '0.5rem', padding: '0.5rem', backgroundColor: '#fff3e0', borderRadius: '4px' }}>
                        <strong>🔍 Anomalies Detected:</strong>
                        <ul style={{ margin: '0.25rem 0 0 1.25rem', paddingLeft: 0 }}>
                          {fileResult.anomalies.map((anomaly: string, idx: number) => (
                            <li key={idx} style={{ marginTop: '0.15rem' }}>{anomaly}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {fileResult.error && (
                      <div style={{ fontSize: '0.85rem', color: 'red', marginTop: '0.25rem' }}>
                        Error: {fileResult.error}
                      </div>
                    )}
                    {fileResult.upload_id && (
                      <div style={{ fontSize: '0.85rem', color: 'green', marginTop: '0.25rem' }}>
                        Upload ID: {fileResult.upload_id}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Supported Formats */}
      <div className="card">
        <h3 className="card-title">Supported File Formats</h3>
        <div className="import-types-grid">
          <div className="import-type-card">
            <h4>📄 PDF</h4>
            <p>Financial documents in PDF format. Document type auto-detected from filename.</p>
          </div>
          <div className="import-type-card">
            <h4>📊 Excel</h4>
            <p>Excel files (.xlsx, .xls) for financial data import</p>
          </div>
          <div className="import-type-card">
            <h4>📋 CSV</h4>
            <p>Comma-separated values files for data import</p>
          </div>
          <div className="import-type-card">
            <h4>📝 DOC</h4>
            <p>Word documents (.doc, .docx) containing financial data</p>
          </div>
        </div>
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
          <strong>Filename Patterns for Auto-Detection:</strong>
          <ul style={{ marginTop: '0.5rem', marginLeft: '1.5rem' }}>
            <li>Balance Sheet: *balance*sheet*, *balance*, *bs*</li>
            <li>Income Statement: *income*statement*, *income*, *p&l*, *profit*loss*</li>
            <li>Cash Flow: *cash*flow*, *cf*, *cashflow*</li>
            <li>Rent Roll: *rent*roll*, *rentroll*, *lease*roll*</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
