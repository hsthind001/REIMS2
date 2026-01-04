import { useState, useEffect, useRef } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'

// Set up PDF.js worker
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`
  console.log('PDF.js worker configured:', pdfjs.GlobalWorkerOptions.workerSrc)
}

interface AnomalyPDFViewerProps {
  pdfUrl: string
  coordinates?: {
    x0: number
    y0: number
    x1: number
    y1: number
    page_number: number
  } | null
  highlightType: 'actual' | 'expected'
  onClose: () => void
}

export function AnomalyPDFViewer({
  pdfUrl,
  coordinates,
  highlightType,
  onClose
}: AnomalyPDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(coordinates?.page_number || 1)
  const [scale, setScale] = useState<number>(1.5) // Start zoomed in for better visibility
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [pageDimensions, setPageDimensions] = useState<{ width: number; height: number } | null>(null)
  const pageRef = useRef<HTMLDivElement>(null)

  // Navigate to the correct page when coordinates are available
  useEffect(() => {
    if (coordinates?.page_number) {
      setPageNumber(coordinates.page_number)
    }
  }, [coordinates])

  // Log PDF URL for debugging
  useEffect(() => {
    if (pdfUrl) {
      console.log('AnomalyPDFViewer: PDF URL:', pdfUrl)
      console.log('AnomalyPDFViewer: Coordinates:', coordinates)
    }
  }, [pdfUrl, coordinates])

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('AnomalyPDFViewer: PDF loaded successfully, pages:', numPages)
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('AnomalyPDFViewer: PDF Load Error:', error)
    console.error('AnomalyPDFViewer: PDF URL:', pdfUrl)
    // Set error to trigger iframe fallback
    setError('Using iframe fallback')
    setLoading(false)
  }

  const onPageLoadSuccess = (page: any) => {
    const viewport = page.getViewport({ scale: 1 })
    setPageDimensions({
      width: viewport.width,
      height: viewport.height
    })
  }

  const goToPrevPage = () => {
    setPageNumber((prev) => Math.max(1, prev - 1))
  }

  const goToNextPage = () => {
    setPageNumber((prev) => Math.min(numPages, prev + 1))
  }

  const zoomIn = () => {
    setScale((prev) => Math.min(3.0, prev + 0.25))
  }

  const zoomOut = () => {
    setScale((prev) => Math.max(0.5, prev - 0.25))
  }

  // Calculate highlight position in viewport coordinates
  const getHighlightStyle = () => {
    if (!coordinates || !pageDimensions || pageNumber !== coordinates.page_number) {
      return null
    }

    // PDF coordinates use bottom-left origin (0,0 at bottom-left)
    // CSS uses top-left origin, so we need to flip Y coordinates
    // pageDimensions are in points (from getViewport)
    // Database coordinates are also in points
    const pageHeight = pageDimensions.height
    const pageWidth = pageDimensions.width
    
    // Convert PDF coordinates to percentages (works with any scale)
    const x0Percent = (coordinates.x0 / pageWidth) * 100
    const x1Percent = (coordinates.x1 / pageWidth) * 100
    
    // Y coordinates need to be flipped (PDF: bottom-left, CSS: top-left)
    // PDF Y is from bottom, CSS Y is from top
    const y0PDF = coordinates.y0 // PDF Y coordinate (from bottom)
    const y1PDF = coordinates.y1 // PDF Y coordinate (from bottom)
    
    // Convert to CSS Y (from top): CSS_Y = pageHeight - PDF_Y
    const y0CSS = pageHeight - y1PDF // Top of highlight in CSS
    const y1CSS = pageHeight - y0PDF // Bottom of highlight in CSS
    
    const y0Percent = (y0CSS / pageHeight) * 100
    const widthPercent = x1Percent - x0Percent
    const heightPercent = ((y1CSS - y0CSS) / pageHeight) * 100

    return {
      position: 'absolute' as const,
      left: `${x0Percent}%`,
      top: `${y0Percent}%`,
      width: `${widthPercent}%`,
      height: `${heightPercent}%`,
      border: `3px solid ${highlightType === 'actual' ? '#ffc107' : '#17a2b8'}`,
      borderRadius: '4px',
      backgroundColor: highlightType === 'actual' ? 'rgba(255, 193, 7, 0.2)' : 'rgba(23, 162, 184, 0.2)',
      pointerEvents: 'none' as const,
      zIndex: 10,
      boxShadow: `0 0 8px ${highlightType === 'actual' ? 'rgba(255, 193, 7, 0.5)' : 'rgba(23, 162, 184, 0.5)'}`
    }
  }

  const highlightStyle = getHighlightStyle()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'white' }}>
      {/* Header with controls */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        padding: '1rem', 
        borderBottom: '1px solid #e5e7eb', 
        backgroundColor: '#f9fafb' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            style={{
              padding: '0.5rem',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: pageNumber <= 1 ? 'not-allowed' : 'pointer',
              opacity: pageNumber <= 1 ? 0.5 : 1
            }}
            onMouseOver={(e) => pageNumber > 1 && (e.currentTarget.style.backgroundColor = '#f3f4f6')}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            title="Previous page"
          >
            <ChevronLeft size={20} />
          </button>
          <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
            Page {pageNumber} of {numPages || '?'}
          </span>
          <button
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
            style={{
              padding: '0.5rem',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: pageNumber >= numPages ? 'not-allowed' : 'pointer',
              opacity: pageNumber >= numPages ? 0.5 : 1
            }}
            onMouseOver={(e) => pageNumber < numPages && (e.currentTarget.style.backgroundColor = '#f3f4f6')}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            title="Next page"
          >
            <ChevronRight size={20} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '1rem' }}>
            <button
              onClick={zoomOut}
              disabled={scale <= 0.5}
              style={{
                padding: '0.5rem',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: 'transparent',
                cursor: scale <= 0.5 ? 'not-allowed' : 'pointer',
                opacity: scale <= 0.5 ? 0.5 : 1
              }}
              onMouseOver={(e) => scale > 0.5 && (e.currentTarget.style.backgroundColor = '#f3f4f6')}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              title="Zoom out"
            >
              <ZoomOut size={20} />
            </button>
            <span style={{ fontSize: '0.875rem', width: '4rem', textAlign: 'center' }}>{Math.round(scale * 100)}%</span>
            <button
              onClick={zoomIn}
              disabled={scale >= 3.0}
              style={{
                padding: '0.5rem',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: 'transparent',
                cursor: scale >= 3.0 ? 'not-allowed' : 'pointer',
                opacity: scale >= 3.0 ? 0.5 : 1
              }}
              onMouseOver={(e) => scale < 3.0 && (e.currentTarget.style.backgroundColor = '#f3f4f6')}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              title="Zoom in"
            >
              <ZoomIn size={20} />
            </button>
          </div>
          {coordinates && (
            <div style={{
              marginLeft: '1rem',
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: '500',
              backgroundColor: highlightType === 'actual' ? '#fff3cd' : '#d1ecf1',
              color: highlightType === 'actual' ? '#856404' : '#0c5460'
            }}>
              {highlightType === 'actual' ? '📍 Actual Value' : '📍 Expected Value'}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '0.5rem',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          title="Close"
        >
          <X size={20} />
        </button>
      </div>

      {/* PDF Content */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto', 
        padding: '1rem', 
        display: 'flex', 
        justifyContent: 'center', 
        backgroundColor: '#f9fafb' 
      }}>
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
              <p style={{ color: '#6b7280' }}>Loading PDF...</p>
            </div>
          </div>
        )}

        {error && pdfUrl && pdfUrl.trim() !== '' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', width: '100%' }}>
            {error !== 'Using iframe fallback' && (
              <div style={{ 
                textAlign: 'center', 
                color: '#dc2626', 
                marginBottom: '1rem', 
                backgroundColor: '#fef2f2', 
                padding: '1rem', 
                borderRadius: '4px', 
                border: '1px solid #fecaca' 
              }}>
                <p style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>PDF Viewer Error</p>
                <p style={{ fontSize: '0.875rem' }}>Using browser PDF viewer as fallback.</p>
              </div>
            )}
            <div style={{ width: '100%', height: '100%', border: '1px solid #d1d5db', borderRadius: '4px' }}>
              <iframe
                src={pdfUrl}
                style={{ width: '100%', height: '100%', border: 'none', minHeight: '600px' }}
                title="PDF Viewer"
              />
            </div>
          </div>
        )}

        {!loading && !error && pdfUrl && pdfUrl.trim() !== '' && (
          <div style={{ position: 'relative', display: 'inline-block' }} ref={pageRef}>
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '24rem' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    border: '3px solid #e5e7eb',
                    borderTop: '3px solid #2563eb',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    marginBottom: '1rem'
                  }}></div>
                  <p style={{ color: '#6b7280' }}>Loading PDF...</p>
                </div>
              }
              options={{
                httpHeaders: {
                  'Accept': 'application/pdf',
                },
                withCredentials: false,
                cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
                cMapPacked: true,
                standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
              }}
            >
              <div style={{ position: 'relative', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}>
                <Page
                  pageNumber={pageNumber}
                  scale={scale}
                  onLoadSuccess={onPageLoadSuccess}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
                
                {/* Highlight overlay */}
                {highlightStyle && (
                  <div style={highlightStyle} />
                )}
              </div>
            </Document>
          </div>
        )}
        
        {!loading && !error && (!pdfUrl || pdfUrl.trim() === '') && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '2rem' }}>
            <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📄</div>
              <p style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>PDF URL Not Available</p>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                The PDF file URL could not be generated. Please check if the document exists in storage.
              </p>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  )
}
