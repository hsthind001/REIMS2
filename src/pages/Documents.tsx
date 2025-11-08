import { useState, useEffect } from 'react'
import { documentService } from '../lib/document'
import { propertyService } from '../lib/property'
import type { Property, DocumentUpload } from '../types/api'

const Documents = () => {
  const [uploading, setUploading] = useState(false)
  const [selectedProperty, setSelectedProperty] = useState('')
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1)
  const [selectedDocType, setSelectedDocType] = useState<'balance_sheet' | 'income_statement' | 'cash_flow' | 'rent_roll'>('balance_sheet')
  const [properties, setProperties] = useState<Property[]>([])
  const [recentUploads, setRecentUploads] = useState<DocumentUpload[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadProperties()
    loadRecentUploads()
  }, [])

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties()
      setProperties(data)
    } catch (error) {
      console.error('Failed to load properties:', error)
    }
  }

  const loadRecentUploads = async () => {
    try {
      setLoading(true)
      const response = await documentService.getDocuments({ limit: 10 })
      setRecentUploads(response.items || [])
    } catch (error) {
      console.error('Failed to load uploads:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate selections
    if (!selectedProperty) {
      alert('Please select a property first')
      return
    }

    // Validate file is PDF
    if (!file.type.includes('pdf')) {
      alert('Please upload a PDF file')
      return
    }

    setUploading(true)
    
    try {
      const result = await documentService.uploadDocument({
        property_code: selectedProperty,
        period_year: selectedYear,
        period_month: selectedMonth,
        document_type: selectedDocType,
        file: file
      })

      // Check if file already exists at this location
      if (result.file_exists && result.existing_file) {
        const existingFile = result.existing_file
        const sizeKB = (existingFile.size / 1024).toFixed(1)
        const lastModified = new Date(existingFile.last_modified).toLocaleString()
        
        const confirmOverwrite = window.confirm(
          `⚠️  FILE ALREADY EXISTS!\n\n` +
          `Path: ${existingFile.path}\n` +
          `Size: ${sizeKB} KB\n` +
          `Last Modified: ${lastModified}\n\n` +
          `Do you want to REPLACE the existing file?\n\n` +
          `Click OK to replace, Cancel to keep existing file.`
        )

        if (!confirmOverwrite) {
          setUploading(false)
          e.target.value = ''  // Reset input
          return
        }

        // User confirmed - upload with overwrite
        const overwriteResult = await documentService.uploadWithOverwrite({
          property_code: selectedProperty,
          period_year: selectedYear,
          period_month: selectedMonth,
          document_type: selectedDocType,
          file: file,
          overwrite: true
        })

        await loadRecentUploads()
        alert(`✅ File replaced successfully!\n\nUpload ID: ${overwriteResult.upload_id}\nStatus: ${overwriteResult.extraction_status}\n\nExtraction task started.`)
        e.target.value = ''
      } else {
        // New file uploaded successfully
        await loadRecentUploads()
        alert(`✅ File uploaded successfully!\n\nUpload ID: ${result.upload_id}\nStatus: ${result.extraction_status}\n\nExtraction task started. Check Dashboard for progress.`)
        e.target.value = ''
      }
      
    } catch (error: any) {
      alert(`❌ Upload failed: ${error.message || 'Unknown error'}`)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Documents</h2>
          <p className="page-subtitle">Upload and manage financial documents</p>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Upload Section */}
        <div className="card wide">
          <h3>Upload Document</h3>
          
          {/* Selection Form */}
          <div className="upload-form" style={{ marginBottom: '1.5rem' }}>
            <div className="form-group">
              <label><strong>Property *</strong></label>
              <select 
                value={selectedProperty} 
                onChange={(e) => setSelectedProperty(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                required
              >
                <option value="">Select property...</option>
                {properties.map(p => (
                  <option key={p.id} value={p.property_code}>
                    {p.property_code} - {p.property_name}
                  </option>
                ))}
              </select>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label><strong>Year *</strong></label>
                <input 
                  type="number" 
                  value={selectedYear} 
                  onChange={(e) => setSelectedYear(parseInt(e.target.value))} 
                  min="2000" 
                  max="2100"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                />
              </div>
              
              <div className="form-group">
                <label><strong>Month *</strong></label>
                <select 
                  value={selectedMonth} 
                  onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  {Array.from({length: 12}, (_, i) => (
                    <option key={i+1} value={i+1}>
                      {new Date(2000, i).toLocaleString('default', { month: 'long' })}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="form-group">
              <label><strong>Document Type *</strong></label>
              <select 
                value={selectedDocType} 
                onChange={(e) => setSelectedDocType(e.target.value as any)}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="balance_sheet">📊 Balance Sheet</option>
                <option value="income_statement">💰 Income Statement</option>
                <option value="cash_flow">💵 Cash Flow Statement</option>
                <option value="rent_roll">🏠 Rent Roll</option>
              </select>
            </div>
          </div>
          
          <div className="upload-area">
            <div className="upload-icon">📤</div>
            <p>Drag and drop files here or click to browse</p>
            <input
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.xlsx,.xls"
              className="file-input"
              disabled={uploading}
            />
            <p className="upload-hint">
              Supported formats: PDF, Excel (XLSX, XLS)
            </p>
            {uploading && <p className="uploading-text">Uploading...</p>}
          </div>
        </div>

        {/* Document Types */}
        <div className="card">
          <h3>Document Types</h3>
          <div className="doc-types">
            <div className="doc-type-item">
              <span className="doc-icon">📊</span>
              <span>Balance Sheet</span>
            </div>
            <div className="doc-type-item">
              <span className="doc-icon">💰</span>
              <span>Income Statement</span>
            </div>
            <div className="doc-type-item">
              <span className="doc-icon">💵</span>
              <span>Cash Flow</span>
            </div>
            <div className="doc-type-item">
              <span className="doc-icon">🏠</span>
              <span>Rent Roll</span>
            </div>
          </div>
        </div>

        {/* Recent Uploads */}
        <div className="card wide">
          <h3>Recent Uploads</h3>
          {loading ? (
            <div className="empty-state">Loading uploads...</div>
          ) : recentUploads.length === 0 ? (
            <div className="empty-state">No documents uploaded yet</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Property</th>
                    <th>Type</th>
                    <th>Period</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {recentUploads.map(doc => (
                    <tr key={doc.id}>
                      <td>{doc.file_name}</td>
                      <td><strong>{doc.property_code}</strong></td>
                      <td style={{ textTransform: 'capitalize' }}>
                        {doc.document_type.replace('_', ' ')}
                      </td>
                      <td>{doc.period_year}/{doc.period_month.toString().padStart(2, '0')}</td>
                      <td>
                        <span className={`status-badge ${doc.extraction_status}`}>
                          {doc.extraction_status}
                        </span>
                      </td>
                      <td>{new Date(doc.upload_date).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Documents

