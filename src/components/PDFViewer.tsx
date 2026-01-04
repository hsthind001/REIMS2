import { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Set up PDF.js worker - use unpkg CDN
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;
  console.log('PDF.js worker configured:', pdfjs.GlobalWorkerOptions.workerSrc);
}

interface PDFViewerProps {
  pdfUrl: string;
  highlightPage?: number;
  highlightCoords?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  onClose?: () => void;
  inline?: boolean; // If true, render inline instead of modal
}

export function PDFViewer({ pdfUrl, highlightPage, highlightCoords, onClose, inline = false }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(highlightPage || 1);
  const [scale, setScale] = useState<number>(1.0); // Start at 100% for readability
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pageDimensions, setPageDimensions] = useState<{ width: number; height: number } | null>(null);
  const loadingRef = useRef(false);

  // Log PDF URL to verify coordinates are included
  useEffect(() => {
    if (pdfUrl && highlightCoords) {
      console.log('📄 PDFViewer: PDF URL with coordinates:', pdfUrl);
      console.log('📍 PDFViewer: Highlight coordinates:', highlightCoords);
      console.log('🔍 PDFViewer: URL includes coordinates?', pdfUrl.includes('x0=') && pdfUrl.includes('y0='));
    }
  }, [pdfUrl, highlightCoords]);

  // Add timeout for PDF loading - but don't show error, just use iframe fallback
  // Reset loading state when PDF URL changes
  useEffect(() => {
    if (pdfUrl) {
      console.log('PDF URL changed, resetting state:', pdfUrl);
      setLoading(true);
      setError(null);
      setPageNumber(highlightPage || 1);
      setNumPages(0);
      setPageDimensions(null);
      
      loadingRef.current = true;
      
      // Set a reasonable timeout - if react-pdf doesn't load in 15 seconds, use iframe
      const timeoutId = setTimeout(() => {
        if (loadingRef.current) {
          console.warn('react-pdf taking too long (>15s), using iframe fallback');
          setError('Using browser PDF viewer');
          setLoading(false);
          loadingRef.current = false;
        }
      }, 15000); // 15 second timeout
      
      return () => {
        clearTimeout(timeoutId);
        loadingRef.current = false;
      };
    }
  }, [pdfUrl, highlightPage]);

  useEffect(() => {
    if (highlightPage) {
      setPageNumber(highlightPage);
    }
  }, [highlightPage]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('✅ PDF loaded successfully with react-pdf, pages:', numPages);
    loadingRef.current = false;
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF Load Error:', error);
    console.error('PDF URL:', pdfUrl);
    loadingRef.current = false;
    // Use iframe fallback for any error
    setError('Using browser PDF viewer');
    setLoading(false);
  };

  const onPageLoadSuccess = (page: any) => {
    const viewport = page.getViewport({ scale: 1 });
    setPageDimensions({
      width: viewport.width,
      height: viewport.height
    });
    
    // If no coordinates but we have highlightPage, try to find text and highlight it
    if (!highlightCoords && highlightPage && pageNumber === highlightPage) {
      // Use PDF.js text layer to search for account codes
      page.getTextContent().then((textContent: any) => {
        const textItems = textContent.items;
        // Look for "1999-0000" or "TOTAL ASSETS"
        for (const item of textItems) {
          if (item.str && (item.str.includes('1999-0000') || item.str.includes('TOTAL ASSETS'))) {
            console.log('Found text to highlight:', item.str);
            // Could implement text-based highlighting here if needed
          }
        }
      }).catch((err: any) => {
        console.warn('Could not extract text for highlighting:', err);
      });
    }
  };

  const goToPrevPage = () => {
    setPageNumber((prev) => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setPageNumber((prev) => Math.min(numPages, prev + 1));
  };

  const zoomIn = () => {
    setScale((prev) => Math.min(3, prev + 0.2));
  };

  const zoomOut = () => {
    setScale((prev) => Math.max(0.5, prev - 0.2));
  };

  const calculateHighlightStyle = () => {
    if (!highlightCoords || !pageDimensions || pageNumber !== highlightPage) {
      return null;
    }

    // PDF coordinates use bottom-left origin (0,0 at bottom-left)
    // CSS uses top-left origin, so we need to flip Y coordinates
    const pageHeight = pageDimensions.height;
    
    // Convert PDF coordinates to CSS coordinates
    // X stays the same, Y needs to be flipped
    const x0Percent = (highlightCoords.x0 / pageDimensions.width) * 100;
    const y0PDF = highlightCoords.y0; // PDF Y coordinate (from bottom)
    const y1PDF = highlightCoords.y1; // PDF Y coordinate (from bottom)
    
    // Convert to CSS Y (from top): CSS_Y = pageHeight - PDF_Y
    const y0CSS = pageHeight - y1PDF; // Top of highlight in CSS
    const y1CSS = pageHeight - y0PDF; // Bottom of highlight in CSS
    
    const y0Percent = (y0CSS / pageHeight) * 100;
    const widthPercent = ((highlightCoords.x1 - highlightCoords.x0) / pageDimensions.width) * 100;
    const heightPercent = ((y1CSS - y0CSS) / pageHeight) * 100;

    return {
      position: 'absolute' as const,
      left: `${x0Percent}%`,
      top: `${y0Percent}%`,
      width: `${widthPercent}%`,
      height: `${heightPercent}%`,
      backgroundColor: 'rgba(255, 255, 0, 0.3)',
      border: '2px solid rgba(255, 200, 0, 0.8)',
      pointerEvents: 'none' as const,
      zIndex: 10,
      boxShadow: '0 0 4px rgba(255, 200, 0, 0.6)',
    };
  };

  // Inline version (for bottom of page)
  if (inline) {
    return (
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 flex flex-col mt-8">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold">Source Document</h3>
            <button
              onClick={goToPrevPage}
              disabled={pageNumber <= 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Previous page"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm font-medium">
              Page {pageNumber} of {numPages || '--'}
            </span>
            <button
              onClick={goToNextPage}
              disabled={pageNumber >= (numPages || 1)}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded hover:bg-gray-100"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* PDF Content */}
        <div className="flex-1 overflow-auto p-4 flex justify-center bg-gray-50 min-h-[600px]">
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
              <div className="text-center text-yellow-600 mb-4 bg-yellow-50 p-4 rounded border border-yellow-200">
                <p className="text-lg font-semibold mb-2">Using browser PDF viewer</p>
                <p className="text-sm mb-2">react-pdf had issues, showing PDF in browser viewer instead.</p>
                {highlightCoords ? (
                  <p className="text-xs text-green-600 mt-2 font-semibold">
                    ✅ Red circle annotation should be visible in the PDF (embedded by backend)
                  </p>
                ) : (
                  <p className="text-xs text-gray-600 mt-2">
                    Note: Highlighting is not available. Coordinates were not captured during extraction.
                  </p>
                )}
              </div>
              <div className="w-full h-full border border-gray-300 rounded relative">
                <iframe
                  src={pdfUrl}
                  className="w-full h-full"
                  title="PDF Viewer"
                  style={{ minHeight: '600px' }}
                  allow="fullscreen"
                  onLoad={(e) => {
                    console.log('PDF iframe loaded, URL:', pdfUrl);
                    // Check if iframe content loaded successfully
                    try {
                      const iframe = e.target as HTMLIFrameElement;
                      // Note: Cross-origin restrictions prevent checking iframe content
                      // But we can log that the iframe loaded
                      console.log('Iframe load event fired');
                    } catch (err) {
                      console.warn('Could not check iframe content (cross-origin):', err);
                    }
                  }}
                  onError={(e) => {
                    console.error('PDF iframe error event:', e);
                  }}
                />
                {/* Error overlay if PDF fails to load */}
                <div 
                  id="pdf-error-overlay" 
                  className="absolute inset-0 bg-white flex items-center justify-center z-20 hidden"
                  style={{ display: 'none' }}
                >
                  <div className="text-center p-4">
                    <p className="text-red-600 font-semibold mb-2">Failed to load PDF</p>
                    <p className="text-sm text-gray-600 mb-2">URL: {pdfUrl.substring(0, 100)}...</p>
                    <p className="text-xs text-gray-500">Check browser console for details</p>
                  </div>
                </div>
                {highlightPage && highlightCoords && (
                  <div className="absolute top-2 left-2 bg-green-100 border border-green-300 rounded p-2 text-xs max-w-xs z-10">
                    <p className="font-semibold">✅ Red Circle Annotation</p>
                    <p className="text-gray-700 mt-1">A red circle should be visible around the value in the PDF.</p>
                    <p className="text-gray-600 mt-1 text-xs">PDF URL: {pdfUrl.substring(0, 80)}...</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {!loading && !error && (
            <div className="relative inline-block">
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className="flex flex-col items-center justify-center h-96">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                    <p className="text-gray-600">Loading PDF with react-pdf...</p>
                    <p className="text-xs text-gray-500 mt-2">This may take a few seconds</p>
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
                  disableAutoFetch: false,
                  disableStream: false,
                  disableRange: false,
                  verbosity: 0,
                }}
              >
                <div className="relative inline-block">
                  <div className="relative">
                    <Page
                      pageNumber={pageNumber}
                      scale={scale}
                      onLoadSuccess={onPageLoadSuccess}
                      className="shadow-lg"
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                      width={undefined}
                    />
                    
                    {/* Highlight overlay - only show if coordinates exist and we're on the right page */}
                    {highlightCoords && pageNumber === highlightPage && pageDimensions && (
                      <div 
                        style={calculateHighlightStyle() || {}}
                        className="absolute pointer-events-none z-10"
                        title="Highlighted value"
                      />
                    )}
                  </div>
                </div>
              </Document>
            </div>
          )}
        </div>

        {/* Footer */}
        {highlightPage && highlightCoords && (
          <div className="p-3 border-t border-gray-200 text-sm text-gray-600 text-center bg-blue-50">
            <p>Highlighted value on page {highlightPage}</p>
          </div>
        )}
      </div>
    );
  }

  // Modal version (original)
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-2xl max-w-7xl w-full mx-4 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <button
              onClick={goToPrevPage}
              disabled={pageNumber <= 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Previous page"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm font-medium">
              Page {pageNumber} of {numPages}
            </span>
            <button
              onClick={goToNextPage}
              disabled={pageNumber >= numPages}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Next page"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={zoomOut}
                className="p-2 rounded hover:bg-gray-100"
                title="Zoom out"
              >
                <ZoomOut className="w-5 h-5" />
              </button>
              <span className="text-sm w-16 text-center">{Math.round(scale * 100)}%</span>
              <button
                onClick={zoomIn}
                className="p-2 rounded hover:bg-gray-100"
                title="Zoom in"
              >
                <ZoomIn className="w-5 h-5" />
              </button>
            </div>
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
        <div className="flex-1 overflow-auto p-4 flex justify-center bg-gray-100">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading PDF...</p>
              </div>
            </div>
          )}
          
          {error && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-red-600">
                <p className="text-lg font-semibold mb-2">Error loading PDF</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && (
            <div className="relative inline-block">
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className="flex items-center justify-center h-96">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    <p className="ml-4 text-gray-600">Loading PDF...</p>
                  </div>
                }
                error={
                  <div className="flex items-center justify-center h-96">
                    <div className="text-center text-red-600">
                      <p className="text-lg font-semibold mb-2">Error loading PDF</p>
                      <p className="text-sm">Please check the browser console for details</p>
                    </div>
                  </div>
                }
                options={{
                  httpHeaders: {},
                  withCredentials: false,
                }}
              >
                <div className="relative inline-block">
                  <Page
                    pageNumber={pageNumber}
                    scale={scale}
                    onLoadSuccess={onPageLoadSuccess}
                    className="shadow-lg"
                  />
                  
                  {/* Highlight overlay - positioned absolutely over the PDF page */}
                  {highlightCoords && pageNumber === highlightPage && pageDimensions && (
                    <div 
                      style={calculateHighlightStyle() || {}}
                      className="absolute"
                    />
                  )}
                </div>
              </Document>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 text-sm text-gray-600 text-center">
          {highlightPage && highlightCoords && (
            <p className="mb-1">
              Highlighted value on page {highlightPage}
            </p>
          )}
          <p>Click outside to close</p>
        </div>
      </div>
    </div>
  );
}
