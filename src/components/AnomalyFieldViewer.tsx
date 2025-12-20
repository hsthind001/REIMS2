import { useState, useEffect } from 'react'
import { AnomalyPDFViewer } from './AnomalyPDFViewer'
import { api } from '../lib/api'

// Temporary inline types and service to work around module resolution issue
export interface FieldCoordinatesResponse {
  has_coordinates: boolean
  coordinates?: {
    x0: number
    y0: number
    x1: number
    y1: number
    page_number: number
  } | null
  pdf_url: string | null
  explanation: string
}

const anomaliesService = {
  async getFieldCoordinates(anomalyId: number): Promise<FieldCoordinatesResponse> {
    try {
      return await api.get<FieldCoordinatesResponse>(`/anomalies/${anomalyId}/field-coordinates`)
    } catch (error: any) {
      console.error('Failed to get field coordinates:', error)
      throw new Error(error.message || 'Failed to get field coordinates')
    }
  }
}

interface Anomaly {
  record_id?: number
  field_name?: string
  value?: number
  details: {
    property_code?: string
    period_year?: number
    period_month?: number
    document_type?: string
    file_name?: string
    field_value?: string | number
    expected_value?: string
    account_name?: string
  }
}

interface AnomalyFieldViewerProps {
  anomaly: Anomaly
  fieldType: 'actual' | 'expected'
  isOpen: boolean
  onClose: () => void
}

export function AnomalyFieldViewer({
  anomaly,
  fieldType,
  isOpen,
  onClose
}: AnomalyFieldViewerProps) {
  const [coordinates, setCoordinates] = useState<FieldCoordinatesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && anomaly.record_id) {
      fetchCoordinates()
    } else if (isOpen && !anomaly.record_id) {
      setError('Anomaly record ID is missing. Cannot load field coordinates.')
      setLoading(false)
    }
  }, [isOpen, anomaly.record_id])

  const fetchCoordinates = async () => {
    if (!anomaly.record_id) return

    setLoading(true)
    setError(null)

    try {
      const data = await anomaliesService.getFieldCoordinates(anomaly.record_id)
      console.log('AnomalyFieldViewer: Received coordinates data:', data)
      if (!data.pdf_url) {
        console.warn('AnomalyFieldViewer: PDF URL is missing from response')
        setError('PDF URL is not available. The document may have been deleted or is not accessible.')
      }
      setCoordinates(data)
    } catch (err) {
      console.error('AnomalyFieldViewer: Failed to fetch coordinates:', err)
      setError(err instanceof Error ? err.message : 'Failed to load field coordinates')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Overlay */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 1000,
          cursor: 'pointer'
        }}
        onClick={onClose}
      />

      {/* Side Panel */}
      <div
        style={{
          position: 'fixed',
          right: 0,
          top: 0,
          height: '100%',
          width: '100%',
          maxWidth: '50%',
          backgroundColor: 'white',
          boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.3)',
          zIndex: 1001,
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideIn 0.3s ease-out'
        }}
      >
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '48px',
                height: '48px',
                border: '3px solid #e5e7eb',
                borderTop: '3px solid #2563eb',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 1rem'
              }}></div>
              <p style={{ color: '#6b7280' }}>Loading field information...</p>
            </div>
          </div>
        )}

        {error && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '2rem' }}>
            <div style={{ textAlign: 'center', color: '#dc2626', backgroundColor: '#fef2f2', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fecaca', maxWidth: '28rem' }}>
              <p style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>Error</p>
              <p style={{ fontSize: '0.875rem' }}>{error}</p>
              <button
                onClick={onClose}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#b91c1c'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#dc2626'}
              >
                Close
              </button>
            </div>
          </div>
        )}

        {!loading && !error && coordinates && (
          <>
            {/* Header */}
            <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: '600', margin: 0 }}>
                    {fieldType === 'actual' ? 'Actual Value' : 'Expected Value'} Location
                  </h2>
                  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem', margin: 0 }}>
                    {anomaly.details.account_name || anomaly.field_name} - {anomaly.details.file_name}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  style={{
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    fontSize: '1.25rem'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  title="Close"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Explanation */}
            <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#eff6ff' }}>
              <p style={{ fontSize: '0.875rem', color: '#374151', margin: 0 }}>
                {coordinates.explanation}
              </p>
              {!coordinates.has_coordinates && (
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem', fontStyle: 'italic', margin: '0.5rem 0 0 0' }}>
                  This field is calculated from multiple line items, so a specific location cannot be highlighted.
                </p>
              )}
            </div>

            {/* PDF Viewer or Message */}
            {coordinates.has_coordinates && coordinates.pdf_url ? (
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <AnomalyPDFViewer
                  pdfUrl={coordinates.pdf_url}
                  coordinates={coordinates.coordinates || undefined}
                  highlightType={fieldType}
                  onClose={onClose}
                />
              </div>
            ) : coordinates.pdf_url && coordinates.pdf_url.trim() !== '' ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
                  <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📄</div>
                    <p style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>Field Location Not Available</p>
                    <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                      {coordinates.explanation}
                    </p>
                    <div style={{ marginTop: '1rem' }}>
                      <a
                        href={coordinates.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          padding: '0.5rem 1rem',
                          backgroundColor: '#2563eb',
                          color: 'white',
                          borderRadius: '4px',
                          textDecoration: 'none'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1d4ed8'}
                        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
                      >
                        Open PDF in new tab →
                      </a>
                    </div>
                  </div>
                </div>
                {/* Show PDF in iframe as fallback */}
                <div style={{ height: '24rem', borderTop: '1px solid #e5e7eb' }}>
                  <iframe
                    src={coordinates.pdf_url}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="PDF Viewer"
                  />
                </div>
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
                <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📄</div>
                  <p style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>PDF Not Available</p>
                  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                    {coordinates.explanation}
                  </p>
                  <p style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                    The PDF file may have been deleted or is not accessible.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </>
  )
}

