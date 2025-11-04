/**
 * Document Upload Component
 * 
 * File upload interface with drag-and-drop support
 */

import { useState, useRef, DragEvent } from 'react';
import { documentService } from '../lib/document';
import { propertyService } from '../lib/property';
import type { Property, DocumentUploadRequest } from '../types/api';
import { useEffect } from 'react';

interface DocumentUploadProps {
  onUploadSuccess?: () => void;
}

export function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    property_code: '',
    period_year: new Date().getFullYear(),
    period_month: new Date().getMonth() + 1,
    document_type: 'balance_sheet' as DocumentUploadRequest['document_type'],
  });
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0 && !formData.property_code) {
        setFormData(prev => ({ ...prev, property_code: data[0].property_code }));
      }
    } catch (err) {
      console.error('Failed to load properties', err);
    }
  };

  const handleDrag = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file: File) => {
    // Validate file type
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are allowed');
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File size must be less than 50MB');
      return;
    }

    setSelectedFile(file);
    setError('');
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    if (!formData.property_code) {
      setError('Please select a property');
      return;
    }

    setUploading(true);
    setProgress(0);
    setError('');
    setSuccess('');

    try {
      // Simulate progress (real progress would need XMLHttpRequest)
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const result = await documentService.uploadDocument({
        ...formData,
        file: selectedFile,
      });

      clearInterval(progressInterval);
      setProgress(100);

      setSuccess(`Upload successful! Task ID: ${result.task_id}`);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      setTimeout(() => {
        setSuccess('');
        setProgress(0);
        onUploadSuccess?.();
      }, 2000);

    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-upload-container">
      <h3>Upload Financial Document</h3>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Property *</label>
            <select
              value={formData.property_code}
              onChange={(e) => setFormData({ ...formData, property_code: e.target.value })}
              required
              disabled={uploading}
            >
              <option value="">Select property...</option>
              {properties.map((p) => (
                <option key={p.id} value={p.property_code}>
                  {p.property_code} - {p.property_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Document Type *</label>
            <select
              value={formData.document_type}
              onChange={(e) => setFormData({ ...formData, document_type: e.target.value as any })}
              required
              disabled={uploading}
            >
              <option value="balance_sheet">Balance Sheet</option>
              <option value="income_statement">Income Statement</option>
              <option value="cash_flow">Cash Flow Statement</option>
              <option value="rent_roll">Rent Roll</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Period Year *</label>
            <input
              type="number"
              value={formData.period_year}
              onChange={(e) => setFormData({ ...formData, period_year: Number(e.target.value) })}
              required
              min="2000"
              max="2100"
              disabled={uploading}
            />
          </div>

          <div className="form-group">
            <label>Period Month *</label>
            <select
              value={formData.period_month}
              onChange={(e) => setFormData({ ...formData, period_month: Number(e.target.value) })}
              required
              disabled={uploading}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                <option key={month} value={month}>
                  {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* File Drop Zone */}
        <div
          className={`file-drop-zone ${dragActive ? 'active' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileInputChange}
            style={{ display: 'none' }}
            disabled={uploading}
          />

          {selectedFile ? (
            <>
              <div className="file-icon">📄</div>
              <div className="file-name">{selectedFile.name}</div>
              <div className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
              {!uploading && (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                >
                  Remove
                </button>
              )}
            </>
          ) : (
            <>
              <div className="file-icon">📁</div>
              <p className="drop-text">Drag and drop PDF file here</p>
              <p className="drop-subtext">or click to browse (max 50MB)</p>
            </>
          )}
        </div>

        {/* Progress Bar */}
        {uploading && (
          <div className="progress-container">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="progress-text">{progress}%</div>
          </div>
        )}

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!selectedFile || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </form>
    </div>
  );
}

