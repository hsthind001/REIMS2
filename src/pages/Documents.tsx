import { useState } from 'react'

const Documents = () => {
  const [uploading, setUploading] = useState(false)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    
    // TODO: Implement file upload to backend
    setTimeout(() => {
      setUploading(false)
      alert('Upload functionality will be implemented')
    }, 1000)
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
          <div className="empty-state">
            No documents uploaded yet
          </div>
        </div>
      </div>
    </div>
  )
}

export default Documents

