import { useState, useEffect, useRef } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'

// Set up PDF.js worker
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`
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

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF Load Error:', error)
    setError('Failed to load PDF')
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
    <div className="flex flex-col h-full bg-white">
      {/* Header with controls */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
            title="Previous page"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-sm font-medium">
            Page {pageNumber} of {numPages || '?'}
          </span>
          <button
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
            className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
            title="Next page"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2 ml-4">
            <button
              onClick={zoomOut}
              disabled={scale <= 0.5}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
              title="Zoom out"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <span className="text-sm w-16 text-center">{Math.round(scale * 100)}%</span>
            <button
              onClick={zoomIn}
              disabled={scale >= 3.0}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
              title="Zoom in"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
          </div>
          {coordinates && (
            <div className="ml-4 px-3 py-1 rounded text-xs font-medium"
                 style={{
                   backgroundColor: highlightType === 'actual' ? '#fff3cd' : '#d1ecf1',
                   color: highlightType === 'actual' ? '#856404' : '#0c5460'
                 }}>
              {highlightType === 'actual' ? '📍 Actual Value' : '📍 Expected Value'}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded hover:bg-gray-100"
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto p-4 flex justify-center bg-gray-50">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading PDF...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-center text-red-600 mb-4 bg-red-50 p-4 rounded border border-red-200">
              <p className="text-lg font-semibold mb-2">Failed to load PDF</p>
              <p className="text-sm">Please try again or contact support.</p>
            </div>
            <div className="w-full h-full border border-gray-300 rounded">
              <iframe
                src={pdfUrl}
                className="w-full h-full"
                title="PDF Viewer"
                style={{ minHeight: '600px' }}
              />
            </div>
          </div>
        )}

        {!loading && !error && (
          <div className="relative inline-block" ref={pageRef}>
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex flex-col items-center justify-center h-96">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                  <p className="text-gray-600">Loading PDF...</p>
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
              <div className="relative">
                <Page
                  pageNumber={pageNumber}
                  scale={scale}
                  onLoadSuccess={onPageLoadSuccess}
                  className="shadow-lg"
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
      </div>
    </div>
  )
}

