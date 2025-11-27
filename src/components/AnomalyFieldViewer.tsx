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
    }
  }, [isOpen, anomaly.record_id])

  const fetchCoordinates = async () => {
    if (!anomaly.record_id) return

    setLoading(true)
    setError(null)

    try {
      const data = await anomaliesService.getFieldCoordinates(anomaly.record_id)
      setCoordinates(data)
    } catch (err) {
      console.error('Failed to fetch coordinates:', err)
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
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Side Panel */}
      <div
        className="fixed right-0 top-0 h-full w-full md:w-3/4 lg:w-2/3 xl:w-1/2 bg-white shadow-2xl z-50 flex flex-col"
        style={{ animation: 'slideIn 0.3s ease-out' }}
      >
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading field information...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full p-8">
            <div className="text-center text-red-600 bg-red-50 p-6 rounded-lg border border-red-200 max-w-md">
              <p className="text-lg font-semibold mb-2">Error</p>
              <p className="text-sm">{error}</p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {!loading && !error && coordinates && (
          <>
            {/* Header */}
            <div className="p-4 border-b bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">
                    {fieldType === 'actual' ? 'Actual Value' : 'Expected Value'} Location
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">
                    {anomaly.details.account_name || anomaly.field_name} - {anomaly.details.file_name}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded hover:bg-gray-200"
                  title="Close"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Explanation */}
            <div className="p-4 border-b bg-blue-50">
              <p className="text-sm text-gray-700">
                {coordinates.explanation}
              </p>
              {!coordinates.has_coordinates && (
                <p className="text-xs text-gray-600 mt-2 italic">
                  This field is calculated from multiple line items, so a specific location cannot be highlighted.
                </p>
              )}
            </div>

            {/* PDF Viewer or Message */}
            {coordinates.has_coordinates && coordinates.pdf_url ? (
              <div className="flex-1 overflow-hidden">
                <AnomalyPDFViewer
                  pdfUrl={coordinates.pdf_url}
                  coordinates={coordinates.coordinates || undefined}
                  highlightType={fieldType}
                  onClose={onClose}
                />
              </div>
            ) : coordinates.pdf_url ? (
              <div className="flex-1 flex flex-col">
                <div className="flex-1 flex items-center justify-center p-8">
                  <div className="text-center max-w-md">
                    <div className="text-4xl mb-4">📄</div>
                    <p className="text-lg font-semibold mb-2">Field Location Not Available</p>
                    <p className="text-sm text-gray-600 mb-4">
                      {coordinates.explanation}
                    </p>
                    <div className="mt-4">
                      <a
                        href={coordinates.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Open PDF in new tab →
                      </a>
                    </div>
                  </div>
                </div>
                {/* Show PDF in iframe as fallback */}
                <div className="h-96 border-t">
                  <iframe
                    src={coordinates.pdf_url}
                    className="w-full h-full"
                    title="PDF Viewer"
                  />
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                  <div className="text-4xl mb-4">📄</div>
                  <p className="text-lg font-semibold mb-2">PDF Not Available</p>
                  <p className="text-sm text-gray-600 mb-4">
                    {coordinates.explanation}
                  </p>
                  <p className="text-xs text-gray-500">
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
      `}</style>
    </>
  )
}

